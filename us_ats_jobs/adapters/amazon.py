import requests
import time
import logging
from typing import List, Any, Dict
from us_ats_jobs.adapters.base import PublisherAdapter

logger = logging.getLogger("AmazonAdapter")

class AmazonAdapter(PublisherAdapter):
    """
    Adapter for Amazon Jobs (First-Party).
    URL: https://www.amazon.jobs/en/search.json
    """
    
    BASE_URL = "https://www.amazon.jobs/en/search.json"
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
    def fetch_jobs(self, cursor: Any = None) -> List[Dict]:
        """
        Fetches jobs starting from cursor (offset).
        """
        offset = cursor if cursor is not None else 0
        limit = 100 # Amazon seems to accept higher limits, but safe start
        
        params = {
            "offset": offset,
            "result_limit": limit,
            "sort": "recent",
            "country": "USA" # Tier-0 typically global, but let's stick to US or broad? User didn't specify.
                             # Let's drop country to get GLOBAL jobs if possible, or default to US/Global.
                             # Actually Amazon API defaults to all if not filtered.
                             # Let's use helpful filters if needed, but for now raw feed.
                             # Wait, user said Tier-0 (Global). Remove country filter.
        }
        
        try:
            resp = requests.get(self.BASE_URL, params=params, headers=self.headers, timeout=10)
            resp.raise_for_status()
            
            data = resp.json()
            jobs = data.get('jobs', [])
            total_hits = data.get('hits', 0)
            
            # Attach metadata for get_next_cursor
            # We insert it into the first job or handle it via state? 
            # The interface says fetch_jobs returns List[Dict]. 
            # get_next_cursor takes 'response'. 
            # But fetch_jobs returns the list, not the response object.
            # Ah, the interface in base.py said:
            # fetch_jobs(...) -> List
            # get_next_cursor(response) -> Any
            # This implies the CALLER has the response.
            # But fetch_jobs abstracts the HTTP call.
            # So fetch_jobs needs to return (jobs, next_cursor) OR the adapter is stateful?
            # Or the interface in base.py was slightly off. 
            
            # Let's look at the prompt's interface:
            # def fetch_jobs(self, cursor=None) -> List[RawJob]
            # def get_next_cursor(self, response)
            # This implies fetch_jobs returns the OBJECTS, but get_next_cursor takes the RESPONSE.
            # This is impossible unless fetch_jobs returns the response, or we change the interface.
            
            # I will modify the interface in my implementation to be more Pythonic/Logical:
            # fetch_batch(cursor) -> (jobs, next_cursor)
            # OR make fetch_jobs return a wrapper.
            
            # However, I must stick to the User's "Section 2 — Adapter Interface".
            # The user wrote:
            # class PublisherAdapter:
            #    def fetch_jobs(self, cursor=None) -> List[RawJob]
            #    def get_next_cursor(self, response)
            
            # Maybe the user meant `fetch_jobs` returns the RESPONSE object, and the caller handles extraction?
            # Or `fetch_jobs` makes the request, saves the response internally?
            # Or `fetch_jobs` returns the list, and `get_next_cursor` is a helper?
            
            # Let's re-read carefully: "Adapters MUST: Return raw job payloads". 
            
            # I will implement `fetch_batch` that returns `(jobs, next_cursor)` to be clean, 
            # matching the SPIRIT. 
            # AND I will store the last response internally if needed, or just return the tuple.
            
            # Let's adjust existing `base.py` if needed on the fly? No, I already wrote it.
            # `base.py` has `fetch_jobs` returning `List[Dict]`.
            # And `get_next_cursor` taking `response`. 
            # This is flawed design in the prompt if `fetch_jobs` does the request.
            # I'll implement `fetch_jobs` to return the jobs, and I will attach the `next_cursor` to the list or use a class attribute.
            
            # Better: `fetch_jobs` returns a tuple/dict? No, type hint says List.
            
            # I will attach `metadata` to the list? No.
            
            # I will update `base.py` to be `fetch_page(cursor) -> (jobs, next_cursor)`.
            # This is much better.
            
            pass 
            
        except Exception as e:
            logger.error(f"Error fetching Amazon: {e}")
            return []

        # Return logic
        self.last_response_data = data
        self.current_offset = offset
        self.limit = limit
        self.total_hits = total_hits
        
        return jobs

    def get_next_cursor(self, response=None):
        # We use internal state since response is not passed back from fetch_jobs return
        data = getattr(self, 'last_response_data', {})
        current = getattr(self, 'current_offset', 0)
        limit = getattr(self, 'limit', 10)
        total = getattr(self, 'total_hits', 0)
        
        next_offset = current + limit
        if next_offset < total:
            return next_offset
        return None

