"""
SerpAPI Jobs Adapter

Uses SerpAPI's Google Jobs endpoint to fetch jobs for companies with blocked APIs.
Integrates with SerpAPIQuotaManager for fair distribution.
"""

import requests
import logging
import time
from typing import List, Any, Dict, Optional

from us_ats_jobs.adapters.base import PublisherAdapter
from us_ats_jobs.adapters.quota_manager import get_quota_manager

logger = logging.getLogger("SerpAPIJobsAdapter")

class SerpAPIJobsAdapter(PublisherAdapter):
    """
    Fetches jobs via SerpAPI Google Jobs endpoint.
    Respects quota limits per company.
    """
    
    SERPAPI_URL = "https://serpapi.com/search"
    JOBS_PER_PAGE = 10  # SerpAPI returns 10 jobs per call
    
    def __init__(self, company: str):
        """
        Initialize adapter for a specific company.
        
        Args:
            company: Company name to search for (e.g., "google", "microsoft")
        """
        self.company = company.lower()
        self.quota_manager = get_quota_manager()
        self.last_response = None
        self.current_start = 0
        
    def fetch_jobs(self, cursor: Any = None) -> List[Dict]:
        """
        Fetch jobs from SerpAPI Google Jobs endpoint.
        
        Args:
            cursor: Start index for pagination (0, 10, 20, etc.)
        
        Returns:
            List of raw job dictionaries
        """
        start = cursor if cursor is not None else 0
        self.current_start = start
        
        # Check quota before making call
        if not self.quota_manager.can_fetch(self.company):
            logger.warning(f"Quota exhausted for {self.company}")
            return []
        
        api_key = self.quota_manager.api_key
        if not api_key:
            logger.error("SerpAPI key not configured")
            return []
        
        # Build search query
        query = f"{self.company} jobs"
        
        params = {
            "engine": "google_jobs",
            "q": query,
            "api_key": api_key,
            "start": start,
            "hl": "en",
            "gl": "us"
        }
        
        try:
            logger.info(f"🔍 [SerpAPI] Fetching {self.company} jobs (start={start})")
            
            resp = requests.get(self.SERPAPI_URL, params=params, timeout=30)
            resp.raise_for_status()
            
            # Record the call
            self.quota_manager.record_call(self.company)
            
            data = resp.json()
            self.last_response = data
            
            jobs = data.get("jobs_results", [])
            
            logger.info(f"✅ [SerpAPI] Got {len(jobs)} jobs for {self.company}")
            
            return jobs
            
        except requests.exceptions.RequestException as e:
            logger.error(f"SerpAPI request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"SerpAPI error: {e}")
            return []
    
    def get_next_cursor(self, response=None) -> Any:
        """
        Get next page cursor.
        SerpAPI uses 'start' parameter (0, 10, 20, ...).
        """
        if not self.last_response:
            return None
        
        # Check if more results available
        # SerpAPI doesn't return total count, we check if jobs_results has data
        jobs = self.last_response.get("jobs_results", [])
        
        if len(jobs) < self.JOBS_PER_PAGE:
            # No more pages
            return None
        
        # Check quota before allowing next page
        if not self.quota_manager.can_fetch(self.company):
            logger.info(f"Quota limit reached for {self.company}, stopping pagination")
            return None
        
        return self.current_start + self.JOBS_PER_PAGE
    
    def rate_limit(self):
        """Respect SerpAPI rate limits."""
        time.sleep(1)  # 1 second between calls


def normalize_serpapi_job(job: Dict, company: str) -> Dict:
    """
    Normalize SerpAPI Google Jobs result to standard schema.
    
    SerpAPI returns:
    - title: Job title
    - company_name: Company name
    - location: Location string
    - description: Job description
    - detected_extensions: {posted_at, schedule_type, salary, ...}
    - job_id: Unique ID
    - apply_options: List of apply links
    """
    # Extract salary if available
    extensions = job.get("detected_extensions", {})
    salary = extensions.get("salary")
    
    # Get apply link
    apply_options = job.get("apply_options", [])
    apply_link = apply_options[0].get("link") if apply_options else ""
    
    # Fallback to job share link
    if not apply_link:
        apply_link = job.get("share_link", "")
    
    # Posted date
    posted_at = extensions.get("posted_at", "")
    
    return {
        "job_id": f"serpapi_{company}_{job.get('job_id', '')}",
        "title": job.get("title", ""),
        "company": job.get("company_name", company.title()),
        "location": job.get("location", ""),
        "job_description": job.get("description", ""),
        "job_link": apply_link,
        "source": f"serpapi_{company}",
        "date_posted": posted_at,
        "salary_raw": salary
    }
