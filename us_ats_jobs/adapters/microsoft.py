"""
Microsoft Adapter - Uses SerpAPI Fallback

STATUS: ACTIVE (via SerpAPI)
NOTE: Microsoft Careers (gcsservices) returns 502/403 for direct requests.
      This adapter uses SerpAPI's Google Jobs endpoint as a fallback.
"""

import logging
from typing import List, Any, Dict

from us_ats_jobs.adapters.base import PublisherAdapter
from us_ats_jobs.adapters.serpapi_jobs import SerpAPIJobsAdapter, normalize_serpapi_job

logger = logging.getLogger("MicrosoftAdapter")

class MicrosoftAdapter(PublisherAdapter):
    """
    Microsoft Careers Adapter - Uses SerpAPI fallback.
    """
    
    def __init__(self):
        self.serpapi_adapter = SerpAPIJobsAdapter("microsoft")
        logger.info("MicrosoftAdapter initialized (using SerpAPI fallback)")
        
    def fetch_jobs(self, cursor: Any = None) -> List[Dict]:
        """
        Fetch Microsoft jobs via SerpAPI.
        Returns normalized job dicts.
        """
        raw_jobs = self.serpapi_adapter.fetch_jobs(cursor)
        
        # Normalize to platform schema
        normalized = [normalize_serpapi_job(job, "microsoft") for job in raw_jobs]
        
        return normalized
        
    def get_next_cursor(self, response=None):
        return self.serpapi_adapter.get_next_cursor(response)
    
    def rate_limit(self):
        self.serpapi_adapter.rate_limit()

