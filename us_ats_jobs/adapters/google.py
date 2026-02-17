"""
Google Adapter - Uses SerpAPI Fallback

STATUS: ACTIVE (via SerpAPI)
NOTE: Google discontinued their public Jobs API in 2021.
      This adapter uses SerpAPI's Google Jobs endpoint as a fallback.
"""

import logging
from typing import List, Any, Dict

from us_ats_jobs.adapters.base import PublisherAdapter
from us_ats_jobs.adapters.serpapi_jobs import SerpAPIJobsAdapter, normalize_serpapi_job

logger = logging.getLogger("GoogleAdapter")

class GoogleAdapter(PublisherAdapter):
    """
    Google Careers Adapter - Uses SerpAPI fallback.
    """
    
    def __init__(self):
        self.serpapi_adapter = SerpAPIJobsAdapter("google")
        logger.info("GoogleAdapter initialized (using SerpAPI fallback)")
        
    def fetch_jobs(self, cursor: Any = None) -> List[Dict]:
        """
        Fetch Google jobs via SerpAPI.
        Returns normalized job dicts.
        """
        raw_jobs = self.serpapi_adapter.fetch_jobs(cursor)
        
        # Normalize to platform schema
        normalized = [normalize_serpapi_job(job, "google") for job in raw_jobs]
        
        return normalized
        
    def get_next_cursor(self, response=None):
        return self.serpapi_adapter.get_next_cursor(response)
    
    def rate_limit(self):
        self.serpapi_adapter.rate_limit()

