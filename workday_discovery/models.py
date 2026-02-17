"""
Pydantic models for Workday Tenant Discovery Engine.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class TenantStatus(str, Enum):
    """Status of a Workday tenant."""
    PENDING_VALIDATION = "pending_validation"
    ACTIVE = "active"
    INACTIVE = "inactive"
    VALIDATION_FAILED = "validation_failed"


class DiscoverySource(str, Enum):
    """Source of tenant discovery."""
    CAREER_PAGE_CRAWL = "career_page_crawl"
    SEARCH_ENGINE = "search_engine"
    LINK_FOLLOWING = "link_following"
    COMMUNITY_SEED = "community_seed"
    MANUAL = "manual"


class WorkdayTenant(BaseModel):
    """
    Represents a Workday career site tenant.
    
    Example tenant:
    - tenant_domain: "nvidia.wd5.myworkdayjobs.com"
    - tenant_slug: "nvidia|wd5|NVIDIAExternalCareerSite"
    - shard: "wd5"
    - site_id: "NVIDIAExternalCareerSite"
    """
    id: Optional[int] = None
    company_id: Optional[int] = None  # Links to companies table
    
    # Core identifiers
    tenant_domain: str  # e.g., "nvidia.wd5.myworkdayjobs.com"
    tenant_slug: str    # e.g., "nvidia|wd5|NVIDIAExternalCareerSite"
    tenant_name: str    # e.g., "nvidia" (subdomain prefix)
    shard: str          # e.g., "wd5"
    site_id: str        # e.g., "NVIDIAExternalCareerSite"
    
    # Company metadata
    company_name: Optional[str] = None
    company_domain: Optional[str] = None
    
    # Status and validation
    status: TenantStatus = TenantStatus.PENDING_VALIDATION
    discovery_source: DiscoverySource = DiscoverySource.MANUAL
    
    # Timestamps
    first_discovered_at: Optional[datetime] = None
    last_validated_at: Optional[datetime] = None
    last_ingested_at: Optional[datetime] = None
    
    # Metrics
    job_count_estimate: int = 0
    ingestion_priority: int = Field(default=5, ge=1, le=10)  # 1-10
    validation_failures: int = 0
    consecutive_failures: int = 0
    
    # Circuit breaker
    circuit_open_until: Optional[datetime] = None
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_url(cls, url: str, company_name: Optional[str] = None) -> Optional["WorkdayTenant"]:
        """
        Parse a Workday URL into a WorkdayTenant object.
        
        Supports formats:
        - https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite
        - https://tenant.wd1.myworkdayjobs.com/en-US/site_id
        """
        import re
        from urllib.parse import urlparse
        
        if "myworkdayjobs.com" not in url:
            return None
        
        try:
            parsed = urlparse(url)
            host = parsed.netloc
            
            # Extract tenant and shard from host
            subdomains = host.split(".myworkdayjobs.com")[0]
            parts = subdomains.split(".")
            
            if len(parts) == 2:
                tenant_name = parts[0]
                shard = parts[1]
            else:
                tenant_name = parts[0]
                shard = "wd1"  # Default shard
            
            # Extract site_id from path
            path_segments = [p for p in parsed.path.split("/") if p and len(p) > 2]
            
            # Filter out language codes like 'en-US'
            site_candidates = [p for p in path_segments if not re.match(r'^[a-z]{2}-[A-Z]{2}$', p)]
            
            if site_candidates:
                site_id = site_candidates[0]
            else:
                site_id = "external"
            
            tenant_slug = f"{tenant_name}|{shard}|{site_id}"
            tenant_domain = f"{tenant_name}.{shard}.myworkdayjobs.com"
            
            return cls(
                tenant_domain=tenant_domain,
                tenant_slug=tenant_slug,
                tenant_name=tenant_name,
                shard=shard,
                site_id=site_id,
                company_name=company_name,
                first_discovered_at=datetime.utcnow(),
            )
        except Exception:
            return None
    
    def get_api_url(self) -> str:
        """Get the Workday API URL for fetching jobs."""
        return f"https://{self.tenant_domain}/wday/cxs/{self.tenant_name}/{self.site_id}/jobs"
    
    def get_careers_url(self) -> str:
        """Get the public careers page URL."""
        return f"https://{self.tenant_domain}/{self.site_id}"


class DiscoveryConfig(BaseModel):
    """Configuration for the discovery engine."""
    batch_size: int = 30
    delay_min_seconds: int = 15
    delay_max_seconds: int = 30
    max_batches_per_run: int = 10
    
    # SerpAPI (surgical use only)
    serpapi_enabled: bool = False
    serpapi_daily_limit: int = 50
    serpapi_api_key: Optional[str] = None
    
    # Validation settings
    validation_timeout_seconds: int = 10
    max_validation_retries: int = 2
    
    # Circuit breaker
    failure_threshold: int = 3
    circuit_cooldown_days: int = 7


class ValidationResult(BaseModel):
    """Result of tenant validation."""
    tenant_slug: str
    success: bool
    is_public: bool = False
    pagination_works: bool = False
    job_count: int = 0
    error_message: Optional[str] = None
    response_time_ms: Optional[int] = None
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class DiscoveryResult(BaseModel):
    """Result of a discovery cycle."""
    total_companies_processed: int
    tenants_discovered: int
    tenants_validated: int
    tenants_failed: int
    discovery_source_breakdown: dict = {}
    duration_seconds: float = 0
    errors: List[str] = []
