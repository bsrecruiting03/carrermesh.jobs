import sys
import os
import time
import random
import re
import requests
import psycopg2
from psycopg2 import extras
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Ensure package path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "us_ats_jobs"))

# Try DDG (with fallback warnings)
try:
    from duckduckgo_search import DDGS
    has_search = True
except ImportError:
    has_search = False

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/job_board")

class WorkdayRecoverer:
    def __init__(self):
        self.headers = {
             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.conn = psycopg2.connect(DB_URL)
        self.conn.autocommit = True
        
    def get_broken_companies(self, limit=100):
        with self.conn.cursor(cursor_factory=extras.RealDictCursor) as cur:
            # Companies marked as Workday but having 0 jobs
            # Or companies with "consecutive_failures" > 0
            cur.execute("""
                SELECT c.id, c.name, c.ats_url, c.consecutive_failures
                FROM companies c
                LEFT JOIN jobs j ON c.name = j.company
                WHERE c.ats_provider = 'workday'
                GROUP BY c.id
                HAVING count(j.job_id) = 0
                ORDER BY c.id ASC
                LIMIT %s
            """, (limit,))
            return cur.fetchall()

    def search_ddg(self, query):
        if not has_search:
            print("⚠️ Search library missing")
            return []
            
        print(f"   🔎 Searching: '{query}'")
        
        try:
            with DDGS() as ddgs:
                # Max 2 results to save bandwidth
                results = [r['href'] for r in ddgs.text(query, max_results=2)]
            return results
        except Exception as e:
            print(f"   ⚠️ Search error: {e}")
            return []

    def scan_for_workday_link(self, url):
        """
        Visits the career page and looks for the Workday link.
        """
        print(f"   👀 Scanning: {url}")
        try:
            resp = requests.get(url, headers=self.headers, timeout=15)
            if resp.status_code != 200:
                return None
                
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 1. Check Links
            for a in soup.find_all('a', href=True):
                href = a['href']
                if "myworkdayjobs.com" in href:
                    return href
            
            # 2. Check Iframes
            for iframe in soup.find_all('iframe', src=True):
                src = iframe['src']
                if "myworkdayjobs.com" in src:
                    return src
                    
            return None
        except Exception as e:
            print(f"   ⚠️ Scan error: {e}")
            return None

    def verify_and_clean_workday_url(self, raw_url):
        # We verify by hitting the API: https://host/wday/cxs/tenant/site_id/jobs
        
        if "myworkdayjobs.com" not in raw_url:
            return None, None
            
        try:
            parsed = urlparse(raw_url)
            host = parsed.netloc # nvidia.wd5.myworkdayjobs.com
            
            # Extract parts from Host
            # valid: tenant.wdX.myworkdayjobs.com
            # sometimes: tenant.myworkdayjobs.com (implies wd1)
            
            subdomains = host.split(".myworkdayjobs.com")[0]
            parts = subdomains.split(".")
            
            if len(parts) == 2:
                tenant = parts[0]
                shard = parts[1] # wd5
            else:
                tenant = parts[0]
                shard = "wd1" # Default
                
            # Extract Site ID from Path
            # Path: /NVIDIAExternalCareerSite/ or /en-US/NVIDIAExternalCareerSite/ ...
            path_segments = [p for p in parsed.path.split("/") if p]
            
            # Heuristic: The Site ID is usually the one that is NOT a language code (en-US)
            # But simplest key is: usually the last segment? Or checking typical endpoints.
            # Let's try the *first* segment that looks like a Site ID.
            # But Workday URLs are usually /tenant/site_id/... NO.
            # They are host/site_id/...
            
            if not path_segments:
                # If root, maybe 'external' or 'careers'?
                # Try guessing common site IDs if path is empty?
                candidates = ["external", "careers", "job_board"]
            else:
                # Try the segments. usually len is 1.
                candidates = path_segments
            
            for site_candidate in candidates:
                if len(site_candidate) < 3: continue # skip 'en', 'us'
                
                api_url = f"https://{host}/wday/cxs/{tenant}/{site_candidate}/jobs"
                
                try:
                    resp = requests.post(api_url, json={"limit":1}, headers=self.headers, timeout=5)
                    if resp.status_code == 200:
                        print(f"   ✅ Verified API: {api_url}")
                        slug = f"{tenant}|{shard}|{site_candidate}"
                        return slug, api_url
                except:
                    pass
                    
        except Exception as e:
            print(f"   ⚠️ Verify error: {e}")
        
        return None, None

    def update_company(self, company_id, new_ats_url):
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE companies 
                SET ats_url = %s, 
                    consecutive_failures = 0,
                    circuit_open_until = NULL,
                    last_success_at = NOW()
                WHERE id = %s
            """, (new_ats_url, company_id))
            print(f"   💾 Updated DB for Company ID {company_id}")

    def search_brave(self, query):
        """
        Fallback scraper for Brave Search (search.brave.com).
        """
        try:
            print(f"   🦁 Brave Search: '{query}'")
            # Brave Search requires no API key for basic HTML scraping usually, 
            # but they might have anti-bot.
            url = f"https://search.brave.com/search?q={requests.utils.quote(query)}"
            resp = requests.get(url, headers=self.headers, timeout=15)
            if resp.status_code != 200:
                print(f"   ⚠️ Brave status: {resp.status_code}")
                return []
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            results = []
            
            # Brave results are usually in 'a' tags with class 'result-header' or similar check
            for a in soup.find_all('a', href=True):
                href = a['href']
                # Filter out brave links and junk
                if href.startswith("http") and "brave.com" not in href and "search.brave" not in href:
                    results.append(href)
                    if len(results) >= 2: break
            
            return results
        except Exception as e:
            print(f"   ⚠️ Brave error: {e}")
            return []

    def unified_search(self, query):
        # 1. Try DDG
        res = self.search_ddg(query)
        if res: return res
        
        # 2. Try Brave (Fallback)
        print("   ⚠️ DDG empty. Falling back to Brave...")
        return self.search_brave(query)

    def run(self):
        # Increased limit to cover all 1787 broken companies
        companies = self.get_broken_companies(limit=2000) 
        print(f"🚀 Starting Recovery for {len(companies)} companies...")
        
        successes = 0
        
        for c in companies:
            print(f"\n🔧 Processing: {c['name']} (ID: {c['id']})")
            
            found_wd_link = None
            
            # Strategy 1: Direct Keyword Search
            wd_query = f'{c["name"]} myworkdayjobs'
            print(f"   🔎 Strategy 1: {wd_query}")
            wd_results = self.unified_search(wd_query)
            
            for res in wd_results:
                if "myworkdayjobs.com" in res:
                    found_wd_link = res
                    print(f"   🎯 Found direct Workday link: {res}")
                    break
            
            # Strategy 2: Generic Careers Search (Fallback)
            if not found_wd_link:
                print(f"   🔎 Strategy 2: Generic Search")
                urls = self.unified_search(f"{c['name']} careers")
                for url in urls:
                    link = self.scan_for_workday_link(url)
                    if link:
                        found_wd_link = link
                        break

            if found_wd_link:
                slug, api_url = self.verify_and_clean_workday_url(found_wd_link)
                if slug:
                    print(f"   🎉 RECOVERED: {slug}")
                    self.update_company(c['id'], slug)
                    successes += 1
                else:
                    print(f"   ❌ Could not verify/parse Workday link: {found_wd_link}")
            else:
                print("   ❌ No Workday link found.")
                
            # Ethical Rate Limit
            delay = random.randint(15, 30)
            print(f"   💤 Sleeping {delay}s...")
            time.sleep(delay)

        print(f"\n🏁 Batch Complete. Recovered {successes}/{len(companies)}.")

if __name__ == "__main__":
    recoverer = WorkdayRecoverer()
    recoverer.run()
