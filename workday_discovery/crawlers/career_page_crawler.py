"""
Career Page Crawler

Discovers Workday tenants by crawling company career pages
and scanning for myworkdayjobs.com references.
"""

import re
import logging
import requests
from typing import Optional, List, Set
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from ..models import WorkdayTenant, DiscoverySource

logger = logging.getLogger(__name__)


class CareerPageCrawler:
    """
    Strategy 1: Career Page Crawling (Primary Discovery Method)
    
    For each company domain:
    - Crawl /careers, /jobs, /work-with-us
    - Scan page source for myworkdayjobs.com
    - Extract tenant subdomain if found
    """
    
    KNOWN_CAREER_PATHS = [
        "/careers",
        "/jobs",
        "/careers/",
        "/jobs/",
        "/work-with-us",
        "/join-us",
        "/about/careers",
        "/company/careers",
        "/en/careers",
        "/us/careers",
    ]
    
    WORKDAY_PATTERNS = [
        r"([a-zA-Z0-9_-]+)\.wd(\d+)\.myworkdayjobs\.com",
        r"myworkdayjobs\.com",
    ]
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
    
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    def crawl(self, company_domain: str, company_name: Optional[str] = None) -> List[WorkdayTenant]:
        """
        Crawl a company domain for Workday career site links.
        
        Args:
            company_domain: Company website domain (e.g., "nvidia.com")
            company_name: Optional company name for metadata
            
        Returns:
            List of discovered WorkdayTenant objects
        """
        discovered: List[WorkdayTenant] = []
        seen_slugs: Set[str] = set()
        
        # Normalize domain
        if not company_domain.startswith(("http://", "https://")):
            company_domain = f"https://{company_domain}"
        
        base_url = company_domain.rstrip("/")
        logger.info(f"Crawling career pages for: {base_url}")
        
        # Try each known career path
        for path in self.KNOWN_CAREER_PATHS:
            url = f"{base_url}{path}"
            
            try:
                tenants = self._scan_page(url, company_name)
                for tenant in tenants:
                    if tenant.tenant_slug not in seen_slugs:
                        tenant.discovery_source = DiscoverySource.CAREER_PAGE_CRAWL
                        tenant.company_domain = urlparse(base_url).netloc
                        discovered.append(tenant)
                        seen_slugs.add(tenant.tenant_slug)
                        logger.info(f"   ✅ Found tenant: {tenant.tenant_slug}")
                
                # If we found tenants, we can stop
                if discovered:
                    break
                    
            except Exception as e:
                logger.debug(f"   Failed to scan {path}: {e}")
                continue
        
        return discovered
    
    def _scan_page(self, url: str, company_name: Optional[str] = None) -> List[WorkdayTenant]:
        """Scan a single page for Workday references."""
        tenants: List[WorkdayTenant] = []
        
        try:
            response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            if response.status_code != 200:
                return tenants
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check all links
            for element in soup.find_all(['a', 'iframe', 'script']):
                href = element.get('href') or element.get('src') or ""
                
                if "myworkdayjobs.com" in href:
                    tenant = WorkdayTenant.from_url(href, company_name)
                    if tenant:
                        tenants.append(tenant)
            
            # Also check inline JavaScript for embedded URLs
            for script in soup.find_all('script'):
                if script.string:
                    found_urls = self._extract_workday_urls_from_text(script.string)
                    for url in found_urls:
                        tenant = WorkdayTenant.from_url(url, company_name)
                        if tenant and tenant.tenant_slug not in [t.tenant_slug for t in tenants]:
                            tenants.append(tenant)
            
        except requests.RequestException as e:
            logger.debug(f"Request failed for {url}: {e}")
        
        return tenants
    
    def _extract_workday_urls_from_text(self, text: str) -> List[str]:
        """Extract Workday URLs from text content."""
        pattern = r'https?://[a-zA-Z0-9_-]+\.wd\d+\.myworkdayjobs\.com[^\s"\'\)]*'
        return re.findall(pattern, text)
    
    def scan_for_workday_link(self, url: str) -> Optional[str]:
        """
        Scan a single URL for Workday links.
        Returns the first Workday URL found, or None.
        """
        tenants = self._scan_page(url)
        if tenants:
            return tenants[0].get_careers_url()
        return None
