"""
Career Page Crawler - LLM-Free Workday Discovery

Crawls company career pages and uses PURE REGEX to detect Workday embeds.
NO LLM calls. 100% deterministic.

Strategy:
1. Query companies with career_page_url and unknown/custom ATS
2. HTTP GET each page
3. Regex match for Workday patterns
4. Register discovered endpoints
"""

import os
import sys
import re
import logging
import requests
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CareerPageCrawler")

DATABASE_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

# --- WORKDAY DETECTION PATTERNS (REGEX ONLY) ---

WORKDAY_PATTERNS = [
    # Direct Workday domains
    re.compile(r'([a-zA-Z0-9-]+)\.wd(\d+)?\.myworkdayjobs\.com', re.IGNORECASE),
    re.compile(r'([a-zA-Z0-9-]+)\.myworkdayjobs\.com', re.IGNORECASE),
    
    # Workday API paths
    re.compile(r'/wday/cxs/([^/\s"\']+)', re.IGNORECASE),
    
    # Workday iframe embeds
    re.compile(r'src=["\']([^"\']*myworkdayjobs\.com[^"\']*)["\']', re.IGNORECASE),
    
    # Workday redirect patterns
    re.compile(r'href=["\']([^"\']*myworkdayjobs\.com[^"\']*)["\']', re.IGNORECASE),
]

# Other ATS patterns (for logging, not primary target)
OTHER_ATS_PATTERNS = {
    'greenhouse': re.compile(r'boards\.greenhouse\.io/([a-zA-Z0-9-]+)', re.IGNORECASE),
    'lever': re.compile(r'jobs\.lever\.co/([a-zA-Z0-9-]+)', re.IGNORECASE),
    'icims': re.compile(r'([a-zA-Z0-9-]+)\.icims\.com', re.IGNORECASE),
    'taleo': re.compile(r'([a-zA-Z0-9-]+)\.taleo\.net', re.IGNORECASE),
    'jobvite': re.compile(r'jobs\.jobvite\.com/([^/\s"\']+)', re.IGNORECASE),
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def extract_workday_urls(html: str) -> set:
    """
    Extract all Workday URLs from HTML using regex.
    Returns set of normalized Workday endpoint URLs.
    """
    found = set()
    
    for pattern in WORKDAY_PATTERNS:
        matches = pattern.findall(html)
        for match in matches:
            if isinstance(match, tuple):
                # Handle group captures
                url = match[0] if match[0] else match[1] if len(match) > 1 else None
            else:
                url = match
            
            if url:
                # Normalize to full URL
                if 'myworkdayjobs.com' in url.lower():
                    if not url.startswith('http'):
                        url = 'https://' + url.lstrip('/')
                    found.add(url)
    
    # Also extract full URLs from href/src
    full_urls = re.findall(r'https?://[^\s"\'<>]+myworkdayjobs\.com[^\s"\'<>]*', html, re.IGNORECASE)
    found.update(full_urls)
    
    return found


def detect_other_ats(html: str) -> dict:
    """
    Detect other ATS providers (for logging purposes).
    Returns dict of {ats_name: [slugs]}
    """
    detected = {}
    for ats_name, pattern in OTHER_ATS_PATTERNS.items():
        matches = pattern.findall(html)
        if matches:
            detected[ats_name] = list(set(matches))
    return detected


def normalize_workday_endpoint(url: str) -> dict:
    """
    Parse Workday URL into structured endpoint data.
    """
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        
        if 'myworkdayjobs.com' not in host:
            return None
        
        parts = host.split('.')
        tenant = parts[0]
        
        # Detect shard
        shard = None
        if len(parts) >= 4 and parts[1].startswith('wd'):
            shard = parts[1]
        
        # Extract path
        path = parsed.path.strip('/').split('/')[0] if parsed.path else ''
        if not path or path in ['wday', 'cxs']:
            path = 'External'
        
        # Build canonical URL
        if shard:
            canonical = f"https://{tenant}.{shard}.myworkdayjobs.com/{path}"
        else:
            canonical = f"https://{tenant}.myworkdayjobs.com/{path}"
        
        return {
            'tenant': tenant,
            'shard': shard,
            'path': path,
            'canonical_url': canonical.rstrip('/')
        }
    except Exception as e:
        return None


class CareerPageCrawler:
    """
    Crawls company career pages to discover Workday portals.
    LLM-Free - uses only HTTP GET + Regex.
    """
    
    def __init__(self):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.stats = {
            'pages_crawled': 0,
            'pages_failed': 0,
            'workday_found': 0,
            'other_ats_found': 0,
            'endpoints_registered': 0
        }
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
    
    def get_target_companies(self, limit: int = 500) -> list:
        """
        Get companies with career pages that might have embedded Workday.
        Targets: custom ATS, unknown ATS, or no ATS provider set.
        """
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, name, career_page_url, ats_provider, domain
            FROM companies
            WHERE career_page_url IS NOT NULL
              AND career_page_url != ''
              AND (
                  ats_provider IS NULL 
                  OR ats_provider IN ('custom', 'unknown', 'other', '')
                  OR ats_provider = 'workday'  -- Re-verify existing Workday companies
              )
            ORDER BY last_scraped_at NULLS FIRST
            LIMIT %s
        """, (limit,))
        return cur.fetchall()
    
    def crawl_page(self, url: str, timeout: int = 10) -> tuple:
        """
        Fetch a career page and return (html, error).
        """
        try:
            response = self.session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return response.text, None
        except requests.exceptions.Timeout:
            return None, "timeout"
        except requests.exceptions.ConnectionError:
            return None, "connection_failed"
        except requests.exceptions.HTTPError as e:
            return None, f"http_{e.response.status_code}"
        except Exception as e:
            return None, str(e)
    
    def process_company(self, company: dict) -> dict:
        """
        Process a single company's career page.
        Returns discovery results.
        """
        url = company['career_page_url']
        company_id = company['id']
        company_name = company['name']
        
        # Normalize URL
        if not url.startswith('http'):
            url = 'https://' + url
        
        # Crawl
        html, error = self.crawl_page(url)
        
        if error:
            self.stats['pages_failed'] += 1
            return {'company': company_name, 'error': error}
        
        self.stats['pages_crawled'] += 1
        
        # Extract Workday URLs
        workday_urls = extract_workday_urls(html)
        other_ats = detect_other_ats(html)
        
        results = {
            'company': company_name,
            'company_id': company_id,
            'workday_urls': list(workday_urls),
            'other_ats': other_ats
        }
        
        if workday_urls:
            self.stats['workday_found'] += 1
            logger.info(f"✅ WORKDAY FOUND: {company_name} -> {list(workday_urls)[:3]}")
            
            # Register endpoints
            for url in workday_urls:
                self._register_endpoint(url, company_id, company_name)
        
        if other_ats:
            self.stats['other_ats_found'] += 1
        
        return results
    
    def _register_endpoint(self, url: str, company_id: int, company_name: str):
        """
        Register discovered Workday endpoint.
        NON-DESTRUCTIVE: INSERT ... ON CONFLICT DO NOTHING.
        """
        endpoint = normalize_workday_endpoint(url)
        if not endpoint:
            return
        
        try:
            cur = self.conn.cursor()
            
            # Check if exists
            cur.execute("""
                SELECT id FROM career_endpoints 
                WHERE url = %s OR canonical_url = %s
            """, (endpoint['canonical_url'], endpoint['canonical_url']))
            
            if cur.fetchone():
                # Already exists, update confidence
                cur.execute("""
                    UPDATE career_endpoints 
                    SET confidence_score = LEAST(confidence_score + 0.1, 1.0),
                        last_verified_at = NOW()
                    WHERE url = %s OR canonical_url = %s
                """, (endpoint['canonical_url'], endpoint['canonical_url']))
            else:
                # Insert new
                slug = f"{endpoint['tenant']}/{endpoint.get('path', 'External')}"
                cur.execute("""
                    INSERT INTO career_endpoints (
                        url, canonical_url, ats_provider, ats_slug,
                        company_id, discovered_from, confidence_score, 
                        last_verified_at, active
                    ) VALUES (
                        %s, %s, 'workday', %s,
                        %s, 'career_page_crawler', 0.6,
                        NOW(), TRUE
                    )
                    ON CONFLICT (url) DO NOTHING
                """, (
                    endpoint['canonical_url'],
                    endpoint['canonical_url'],
                    slug,
                    company_id
                ))
                self.stats['endpoints_registered'] += 1
            
            self.conn.commit()
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Failed to register endpoint: {e}")
    
    def run(self, limit: int = 500, workers: int = 5):
        """
        Main crawl loop with threading.
        """
        logger.info(f"🕷️  Starting Career Page Crawler (limit={limit}, workers={workers})...")
        
        companies = self.get_target_companies(limit)
        logger.info(f"📋 Found {len(companies)} companies with career pages to scan")
        
        if not companies:
            logger.info("No companies to scan. Done.")
            return
        
        results = []
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(self.process_company, company): company 
                for company in companies
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Worker error: {e}")
        
        self._report_stats()
        return results
    
    def _report_stats(self):
        logger.info("=" * 50)
        logger.info("📊 Crawl Complete - Statistics:")
        logger.info(f"   Pages Crawled: {self.stats['pages_crawled']}")
        logger.info(f"   Pages Failed: {self.stats['pages_failed']}")
        logger.info(f"   Companies with Workday: {self.stats['workday_found']}")
        logger.info(f"   Companies with Other ATS: {self.stats['other_ats_found']}")
        logger.info(f"   New Endpoints Registered: {self.stats['endpoints_registered']}")
        logger.info("=" * 50)
    
    def close(self):
        if self.conn:
            self.conn.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Career Page Crawler (LLM-Free)')
    parser.add_argument('--limit', type=int, default=100, help='Max companies to crawl')
    parser.add_argument('--workers', type=int, default=5, help='Concurrent workers')
    args = parser.parse_args()
    
    crawler = CareerPageCrawler()
    try:
        crawler.run(limit=args.limit, workers=args.workers)
    finally:
        crawler.close()


if __name__ == "__main__":
    main()
