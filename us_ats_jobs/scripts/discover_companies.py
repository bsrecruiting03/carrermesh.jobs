import sys
import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Add parent directory to path so we can import db
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import db.database as database
database.create_tables()

try:
    from googlesearch import search
except ImportError:
    print("⚠️ 'googlesearch-python' not installed. Falling back to guessing mode.")
    search = None

# Known ATS domains
ATS_DOMAINS = {
    "boards.greenhouse.io": "greenhouse",
    "jobs.lever.co": "lever",
    "jobs.ashbyhq.com": "ashby",
    "apply.workable.com": "workable",
    "bamboohr.com/jobs": "bamboohr",
    # Add more as needed
}

def safe_get(url, retries=3):
    """
    Requests with exponential backoff for 429s.
    """
    delay = 1
    for i in range(retries):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 429:
                print(f"    ⏳ Rate limited. Sleeping {delay}s...")
                time.sleep(delay)
                delay *= 2
                continue
                
            return response
        except Exception as e:
            print(f"    ⚠️ Request failed: {e}")
            return None
    return None

def extract_domain(url):
    """
    Extracts 'stripe.com' from 'https://stripe.com/jobs' or 'sub.stripe.com'.
    """
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc
        # remove www.
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except:
        return None

def get_ats_provider(url):
    parsed = urlparse(url)
    domain = parsed.netloc
    
    # Check exact matches
    if domain in ATS_DOMAINS:
        return ATS_DOMAINS[domain]
        
    # Check subdomains/partial matches
    for ats_domain, provider in ATS_DOMAINS.items():
        if ats_domain in domain:
            return provider
    return None

def find_ats_on_page(url):
    """
    Scrapes a career page to find a link to an ATS.
    """
    try:
        response = safe_get(url)
        if not response or response.status_code != 200:
            return None, None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for links
        for a in soup.find_all('a', href=True):
            href = a['href']
            provider = get_ats_provider(href)
            if provider:
                return href, provider
                
        return None, None
    except Exception as e:
        print(f"  ❌ Error scraping {url}: {e}")
        return None, None

def search_company(company_name):
    """
    Uses Google Search to find the career page, then scrapes it.
    """
    if not search:
        return None, None, None

    query = f"{company_name} careers"
    print(f"  🔎 Searching Google for: '{query}'...")
    
    try:
        # Get top 3 results
        results = list(search(query, num_results=3, lang="en"))
        
        for url in results:
            print(f"    Checking: {url}")
            
            # 1. Check if the result itself is an ATS link
            provider = get_ats_provider(url)
            if provider:
                return url, provider, url # Found direct link
            
            # 2. Scrape the page to find an ATS link
            ats_link, provider = find_ats_on_page(url)
            if ats_link:
                return ats_link, provider, url
                
    except Exception as e:
        print(f"  ⚠️ Search failed: {e}")
        
    return None, None, None

# ------------------------------------------------------------------------------
# Verification Logic
# ------------------------------------------------------------------------------

def verify_ats_content(url, provider):
    """
    Verifies if the page content actually looks like a valid ATS page.
    Fixes the issue where some ATS (like Ashby) return 200 OK for invalid boards.
    """
    try:
        # We need the content, so we might need to fetch again if not passed
        # But safe_get limits retries so it's okay.
        resp = safe_get(url)
        if not resp: 
            return False
        
        # 1. Status Code Check
        if resp.status_code != 200:
            return False
            
        content = resp.text.lower()
        
        # 2. Provider-Specific Content Checks
        if provider == "ashby":
            # Ashby often returns 200 for invalid pages.
            # Invalid pages usually say "Company not found" or redirect to home?
            # Or they might just be empty.
            # Check for specific "Not Found" indicators
            if "company not found" in content or "no such board" in content:
                print(f"    ⚠️  [False Positive] {url} returned 200 but content says Not Found")
                return False
                
            # Check for POSITIVE indicators (at least one job or header)
            # This is strict but safer.
            # Common Ashby class or text? "Current Openings"
            # if "current openings" not in content and "open roles" not in content:
            #     print(f"    ⚠️  [Suspicious] {url} has no standard job header")
            #     # Let's not be too strict yet, but maybe?
            
        # Generic Checks
        if "page not found" in content or "404 - not found" in content:
             return False
             
        return True
        
    except Exception as e:
        print(f"    ⚠️ Verification failed: {e}")
        return False

def discover_and_save(company_name):
    print(f"\n🚀 Discovering: {company_name}")
    
    # 1. Try Search + Crawl
    ats_url, provider, career_page = search_company(company_name)
    
    # 2. Fallback: Guessing
    if not ats_url:
        print("  🤔 No ATS found via search. Trying standard slugs...")
        slug = company_name.lower().replace(" ", "").replace("-", "")
        
        # Prioritize Greenhouse/Lever as they are more reliable with 404s
        guesses = [
            (f"https://boards.greenhouse.io/{slug}", "greenhouse"),
            (f"https://jobs.lever.co/{slug}", "lever"),
            (f"https://apply.workable.com/{slug}", "workable"),
            (f"https://{slug}.bamboohr.com/jobs", "bamboohr"),
            (f"https://jobs.ashbyhq.com/{slug}", "ashby"), # Moved Ashby to end due to false positives
        ]
        
        for url, guess_provider in guesses:
            try:
                # First check status code
                resp = safe_get(url)
                if resp and resp.status_code == 200:
                    # THEN verify content (CRITICAL FIX)
                    if verify_ats_content(url, guess_provider):
                        print(f"    ✅ Guess confirmed: {url}")
                        ats_url = url
                        provider = guess_provider
                        career_page = None 
                        break
                    else:
                        print(f"    ❌ Guess rejected (False Positive): {url}")
            except:
                pass

    # 3. Save
    if ats_url and provider:
        domain = None
        if career_page:
            domain = extract_domain(career_page)
        elif ats_url:
            # If we only have ATS url like boards.greenhouse.io/stripe, 
            # we can't easily get stripe.com without more logic.
            # But for now let's leave it None or try to guess?
            # Ideally we want the REAL domain.
            pass

        print(f"  🎉 SUCCESS! Found {provider} for {company_name}: {ats_url} (Domain: {domain})")
        if database.add_company(company_name, ats_url, provider, career_page, domain):
            print("    💾 Saved to database.")
        else:
            print("    ⚠️ Already in database.")
    else:
        print(f"  ❌ FAILED. Could not find ATS for {company_name}.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Use command line args: python discover_companies.py "Company A" "Company B"
        companies = sys.argv[1:]
    else:
        # Default interactive output
        # If imported as a module, this block won't run, which is what we want.
        if len(sys.argv) == 1: 
             print("Enter company names (comma separated):")
             inp = input("> ")
             companies = [c.strip() for c in inp.split(",") if c.strip()]
        else:
             companies = []

    for c in companies:
        discover_and_save(c)
