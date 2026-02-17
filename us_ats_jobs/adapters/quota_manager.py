"""
SerpAPI Quota Manager - Fair Distribution System

Tracks and enforces per-company daily quota for SerpAPI calls.
Ensures balanced job ingestion across multiple difficult companies.
"""

import os
import logging
from datetime import datetime, date
from typing import Dict, Optional

logger = logging.getLogger("SerpAPIQuotaManager")

class SerpAPIQuotaManager:
    """
    Manages SerpAPI quota distribution across companies.
    Uses in-memory tracking (resets on restart) or can be persisted.
    """
    
    # Default configuration
    TOTAL_DAILY_LIMIT = 100  # SerpAPI free tier
    RESERVED_FOR_DISCOVERY = 20
    DEFAULT_PER_COMPANY_LIMIT = 10
    
    # Companies that need SerpAPI (blocked direct APIs)
    DIFFICULT_COMPANIES = [
        "google",
        "microsoft", 
        "meta",
        "tesla",
        "tiktok",
        "netflix",
        "uber",
        "apple"
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
        self.reset_date = date.today()
        self.company_usage: Dict[str, int] = {}
        self.total_calls_today = 0
        
        # Initialize usage tracking
        for company in self.DIFFICULT_COMPANIES:
            self.company_usage[company] = 0
            
        logger.info(f"SerpAPIQuotaManager initialized. API Key: {'✓' if self.api_key else '✗'}")
    
    def _check_reset(self):
        """Reset counters at midnight."""
        if date.today() != self.reset_date:
            logger.info("🔄 Daily quota reset")
            self.reset_date = date.today()
            self.total_calls_today = 0
            for company in self.company_usage:
                self.company_usage[company] = 0
    
    def can_fetch(self, company: str) -> bool:
        """Check if quota allows fetching for this company."""
        self._check_reset()
        
        if not self.api_key:
            logger.warning("SerpAPI key not configured")
            return False
        
        company_lower = company.lower()
        
        # Global limit check
        available = self.TOTAL_DAILY_LIMIT - self.RESERVED_FOR_DISCOVERY
        if self.total_calls_today >= available:
            logger.warning(f"Global daily limit reached ({available})")
            return False
        
        # Per-company limit check
        current = self.company_usage.get(company_lower, 0)
        if current >= self.DEFAULT_PER_COMPANY_LIMIT:
            logger.warning(f"Daily limit for {company} reached ({self.DEFAULT_PER_COMPANY_LIMIT})")
            return False
            
        return True
    
    def record_call(self, company: str):
        """Record an API call for a company."""
        self._check_reset()
        company_lower = company.lower()
        
        self.total_calls_today += 1
        if company_lower not in self.company_usage:
            self.company_usage[company_lower] = 0
        self.company_usage[company_lower] += 1
        
        logger.debug(f"SerpAPI call recorded: {company} ({self.company_usage[company_lower]}/{self.DEFAULT_PER_COMPANY_LIMIT})")
    
    def get_remaining(self, company: str) -> int:
        """Get remaining calls for a company today."""
        self._check_reset()
        company_lower = company.lower()
        current = self.company_usage.get(company_lower, 0)
        return max(0, self.DEFAULT_PER_COMPANY_LIMIT - current)
    
    def get_global_remaining(self) -> int:
        """Get remaining global calls today."""
        self._check_reset()
        available = self.TOTAL_DAILY_LIMIT - self.RESERVED_FOR_DISCOVERY
        return max(0, available - self.total_calls_today)
    
    def get_status(self) -> dict:
        """Get current quota status for all companies."""
        self._check_reset()
        return {
            "reset_date": str(self.reset_date),
            "total_calls_today": self.total_calls_today,
            "global_remaining": self.get_global_remaining(),
            "companies": {
                company: {
                    "used": self.company_usage.get(company, 0),
                    "remaining": self.get_remaining(company),
                    "limit": self.DEFAULT_PER_COMPANY_LIMIT
                }
                for company in self.DIFFICULT_COMPANIES
            }
        }


# Singleton instance for the application
_quota_manager: Optional[SerpAPIQuotaManager] = None

def get_quota_manager() -> SerpAPIQuotaManager:
    """Get or create the singleton quota manager."""
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = SerpAPIQuotaManager()
    return _quota_manager
