"""
Search Engine Seeder

Discovers Workday tenants using search engine queries.
Uses a tiered approach: DDG -> Brave -> SerpAPI (surgical only).
"""

import re
import os
import logging
import requests
import random
import time
from typing import Optional, List, Set
from urllib.parse import quote

from bs4 import BeautifulSoup

from ..models import WorkdayTenant, DiscoverySource, DiscoveryConfig

logger = logging.getLogger(__name__)

# Optional DDG import
try:
    from duckduckgo_search import DDGS
    HAS_DDG = True
except ImportError:
    HAS_DDG = False
    logger.warning("duckduckgo_search not installed, DDG search disabled")


class SearchEngineSeeder:
    """
    Strategy 2: Search Engine Seeding
    
    Tiered search approach:
    - Tier 1: DuckDuckGo (free, primary)
    - Tier 2: Brave Search (free, fallback)
    - Tier 3: SerpAPI (paid, surgical validation/gap-fill only)
    """
    
    QUERY_TEMPLATES = [
        "{company_name} myworkdayjobs",
        "{company_name} careers workday",
        "site:myworkdayjobs.com {company_name}",
    ]
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    def __init__(self, config: Optional[DiscoveryConfig] = None):
        self.config = config or DiscoveryConfig()
        self.serpapi_calls_today = 0
    
    def search(self, company_name: str, use_premium: bool = False) -> List[WorkdayTenant]:
        """
        Search for Workday tenants for a given company.
        
        Args:
            company_name: Name of the company to search for
            use_premium: If True and free engines fail, use SerpAPI
            
        Returns:
            List of discovered WorkdayTenant objects
        """
        tenants: List[WorkdayTenant] = []
        seen_slugs: Set[str] = set()
        
        logger.info(f"🔎 Searching for Workday tenant: {company_name}")
        
        # Try each query template
        for template in self.QUERY_TEMPLATES:
            query = template.format(company_name=company_name)
            
            # Tier 1: DDG
            results = self._search_ddg(query)
            
            # Tier 2: Brave fallback
            if not results:
                logger.debug("   DDG empty, trying Brave...")
                results = self._search_brave(query)
            
            # Parse results
            for url in results:
                if "myworkdayjobs.com" in url:
                    tenant = WorkdayTenant.from_url(url, company_name)
                    if tenant and tenant.tenant_slug not in seen_slugs:
                        tenant.discovery_source = DiscoverySource.SEARCH_ENGINE
                        tenants.append(tenant)
                        seen_slugs.add(tenant.tenant_slug)
                        logger.info(f"   🎯 Found: {tenant.tenant_slug}")
            
            if tenants:
                break  # Found what we need
        
        # Tier 3: SerpAPI (surgical only)
        if not tenants and use_premium:
            tenants = self._search_serpapi_surgical(company_name)
        
        return tenants
    
    def _search_ddg(self, query: str, max_results: int = 3) -> List[str]:
        """Search using DuckDuckGo."""
        if not HAS_DDG:
            return []
        
        try:
            with DDGS() as ddgs:
                results = [r['href'] for r in ddgs.text(query, max_results=max_results)]
            return results
        except Exception as e:
            logger.debug(f"DDG search failed: {e}")
            return []
    
    def _search_brave(self, query: str, max_results: int = 3) -> List[str]:
        """Search using Brave Search (HTML scraping)."""
        try:
            url = f"https://search.brave.com/search?q={quote(query)}"
            response = requests.get(url, headers=self.HEADERS, timeout=15)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results = []
            
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.startswith("http") and "brave.com" not in href:
                    results.append(href)
                    if len(results) >= max_results:
                        break
            
            return results
        except Exception as e:
            logger.debug(f"Brave search failed: {e}")
            return []
    
    def _search_serpapi_surgical(self, company_name: str) -> List[WorkdayTenant]:
        """
        SerpAPI search - SURGICAL USE ONLY.
        
        Only used for:
        - Validation failures after free engines fail
        - High-value gap-filling (Fortune 50)
        - Periodic re-validation
        """
        if not self.config.serpapi_enabled:
            return []
        
        if not self.config.serpapi_api_key:
            logger.warning("SerpAPI enabled but no API key configured")
            return []
        
        if self.serpapi_calls_today >= self.config.serpapi_daily_limit:
            logger.warning(f"SerpAPI daily limit reached ({self.config.serpapi_daily_limit})")
            return []
        
        try:
            logger.info(f"   💰 [SERPAPI] Premium search for: {company_name}")
            self.serpapi_calls_today += 1
            
            query = f"{company_name} myworkdayjobs"
            url = "https://serpapi.com/search"
            params = {
                "q": query,
                "api_key": self.config.serpapi_api_key,
                "engine": "google",
                "num": 5,
            }
            
            response = requests.get(url, params=params, timeout=15)
            if response.status_code != 200:
                return []
            
            data = response.json()
            tenants = []
            
            for result in data.get("organic_results", []):
                link = result.get("link", "")
                if "myworkdayjobs.com" in link:
                    tenant = WorkdayTenant.from_url(link, company_name)
                    if tenant:
                        tenant.discovery_source = DiscoverySource.SEARCH_ENGINE
                        tenants.append(tenant)
                        logger.info(f"   🎯 [SERPAPI] Found: {tenant.tenant_slug}")
            
            return tenants
            
        except Exception as e:
            logger.error(f"SerpAPI search failed: {e}")
            return []
    
    def reset_daily_counter(self):
        """Reset the daily SerpAPI call counter."""
        self.serpapi_calls_today = 0
    
    def get_serpapi_usage(self) -> dict:
        """Get current SerpAPI usage stats."""
        return {
            "calls_today": self.serpapi_calls_today,
            "daily_limit": self.config.serpapi_daily_limit,
            "remaining": self.config.serpapi_daily_limit - self.serpapi_calls_today,
        }
