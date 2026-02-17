"""
Link Follower

Discovers additional Workday tenants by following links from known tenants.
Identifies shared Workday environments and cross-references.
"""

import re
import logging
import requests
from typing import List, Set, Optional
from urllib.parse import urlparse

from ..models import WorkdayTenant, DiscoverySource

logger = logging.getLogger(__name__)


class LinkFollower:
    """
    Strategy 3: Link Following from Known Tenants
    
    Once a tenant is discovered:
    - Fetch job listings from the tenant
    - Extract references to other myworkdayjobs.com domains
    - Discover shared Workday environments
    """
    
    HEADERS = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    def discover_related_tenants(self, known_tenant: WorkdayTenant) -> List[WorkdayTenant]:
        """
        Discover related tenants from a known tenant's job listings.
        
        Some companies have multiple career sites or shared environments:
        - NVIDIA has site for early careers, experienced, etc.
        - WME|IMG has 8+ distinct career sites
        
        Args:
            known_tenant: A validated WorkdayTenant to scan for related tenants
            
        Returns:
            List of newly discovered WorkdayTenant objects
        """
        discovered: List[WorkdayTenant] = []
        seen_slugs: Set[str] = set([known_tenant.tenant_slug])
        
        logger.info(f"🔗 Following links from: {known_tenant.tenant_slug}")
        
        try:
            # Fetch jobs from the known tenant
            api_url = known_tenant.get_api_url()
            payload = {
                "appliedFacets": {},
                "limit": 50,
                "offset": 0,
                "searchText": "",
            }
            
            response = self.session.post(api_url, json=payload, timeout=self.timeout)
            if response.status_code != 200:
                logger.debug(f"   Failed to fetch jobs: {response.status_code}")
                return discovered
            
            data = response.json()
            
            # Scan job data for other tenant references
            text_content = str(data)
            related_urls = self._extract_workday_urls(text_content)
            
            for url in related_urls:
                tenant = WorkdayTenant.from_url(url)
                if tenant and tenant.tenant_slug not in seen_slugs:
                    # Check if it's actually a different tenant (not just same tenant different path)
                    if tenant.tenant_name != known_tenant.tenant_name or tenant.site_id != known_tenant.site_id:
                        tenant.discovery_source = DiscoverySource.LINK_FOLLOWING
                        tenant.company_name = known_tenant.company_name
                        discovered.append(tenant)
                        seen_slugs.add(tenant.tenant_slug)
                        logger.info(f"   🔗 Found related: {tenant.tenant_slug}")
            
            # Also check the career page HTML for additional links
            career_page_tenants = self._scan_career_page(known_tenant)
            for tenant in career_page_tenants:
                if tenant.tenant_slug not in seen_slugs:
                    discovered.append(tenant)
                    seen_slugs.add(tenant.tenant_slug)
            
        except Exception as e:
            logger.debug(f"   Link following error: {e}")
        
        return discovered
    
    def _extract_workday_urls(self, text: str) -> List[str]:
        """Extract Workday URLs from text content."""
        pattern = r'https?://[a-zA-Z0-9_-]+\.wd\d+\.myworkdayjobs\.com[^\s"\'\)]*'
        urls = re.findall(pattern, text)
        return list(set(urls))  # Deduplicate
    
    def _scan_career_page(self, tenant: WorkdayTenant) -> List[WorkdayTenant]:
        """Scan the tenant's career page for additional site links."""
        tenants: List[WorkdayTenant] = []
        
        try:
            # Get the main career page HTML
            url = f"https://{tenant.tenant_domain}/"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code != 200:
                return tenants
            
            # Look for links to other sites
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                if "myworkdayjobs.com" in href and href != url:
                    new_tenant = WorkdayTenant.from_url(href, tenant.company_name)
                    if new_tenant:
                        new_tenant.discovery_source = DiscoverySource.LINK_FOLLOWING
                        tenants.append(new_tenant)
        
        except Exception as e:
            logger.debug(f"Career page scan error: {e}")
        
        return tenants
    
    def follow_all_known_tenants(self, tenants: List[WorkdayTenant]) -> List[WorkdayTenant]:
        """
        Follow links from all known tenants to discover related ones.
        
        Args:
            tenants: List of known WorkdayTenant objects
            
        Returns:
            List of all newly discovered tenants
        """
        all_discovered: List[WorkdayTenant] = []
        all_slugs: Set[str] = set(t.tenant_slug for t in tenants)
        
        for tenant in tenants:
            related = self.discover_related_tenants(tenant)
            for new_tenant in related:
                if new_tenant.tenant_slug not in all_slugs:
                    all_discovered.append(new_tenant)
                    all_slugs.add(new_tenant.tenant_slug)
        
        return all_discovered
