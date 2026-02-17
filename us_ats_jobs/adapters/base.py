from abc import ABC, abstractmethod
from typing import List, Any, Dict

class PublisherAdapter(ABC):
    """
    Abstract Base Class for First-Party Publisher Adapters.
    
    These adapters are for companies that control their own hiring funnel
    and do NOT use a standard ATS (e.g., Amazon, Google, Microsoft).
    
    They MUST be registered manually in `career_endpoints`.
    """
    
    @abstractmethod
    def fetch_jobs(self, cursor: Any = None) -> List[Dict]:
        """
        Fetches next batch of jobs.
        
        Args:
            cursor: Pagination cursor (offset, page_token, etc.)
            
        Returns:
            List of raw job dictionaries.
        """
        pass
        
    @abstractmethod
    def get_next_cursor(self, response: Any) -> Any:
        """
        Extracts the next cursor from the response.
        Returns None if no more pages.
        """
        pass
        
    def rate_limit(self):
        """
        Optional hook for strict rate limiting.
        """
        pass
