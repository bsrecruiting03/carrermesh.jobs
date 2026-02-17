"""
Netflix Adapter - Uses SerpAPI Fallback

STATUS: ACTIVE (via SerpAPI)
"""

import logging
from typing import List, Any, Dict

from us_ats_jobs.adapters.base import PublisherAdapter
from us_ats_jobs.adapters.serpapi_jobs import SerpAPIJobsAdapter, normalize_serpapi_job

logger = logging.getLogger("NetflixAdapter")

class NetflixAdapter(PublisherAdapter):
    """Netflix Careers Adapter - Uses SerpAPI fallback."""
    
    def __init__(self):
        self.serpapi_adapter = SerpAPIJobsAdapter("netflix")
        logger.info("NetflixAdapter initialized (using SerpAPI fallback)")
        
    def fetch_jobs(self, cursor: Any = None) -> List[Dict]:
        raw_jobs = self.serpapi_adapter.fetch_jobs(cursor)
        return [normalize_serpapi_job(job, "netflix") for job in raw_jobs]
        
    def get_next_cursor(self, response=None):
        return self.serpapi_adapter.get_next_cursor(response)
    
    def rate_limit(self):
        self.serpapi_adapter.rate_limit()
