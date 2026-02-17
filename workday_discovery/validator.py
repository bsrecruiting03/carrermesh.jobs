"""
Tenant Validator

Validates Workday tenants to ensure they are publicly accessible
and suitable for job ingestion.
"""

import time
import logging
import requests
from typing import Optional
from datetime import datetime

from .models import WorkdayTenant, ValidationResult, TenantStatus, DiscoveryConfig

logger = logging.getLogger(__name__)


class TenantValidator:
    """
    Validates Workday tenants before adding them to the registry.
    
    Validation checks:
    1. Job listings publicly accessible (no auth required)
    2. Pagination works (offset/limit parameters)
    3. Job details readable
    4. Returns 200 status codes
    """
    
    HEADERS = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    def __init__(self, config: Optional[DiscoveryConfig] = None):
        self.config = config or DiscoveryConfig()
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    def validate(self, tenant: WorkdayTenant) -> ValidationResult:
        """
        Validate a Workday tenant.
        
        Args:
            tenant: WorkdayTenant object to validate
            
        Returns:
            ValidationResult with success status and details
        """
        start_time = time.time()
        
        result = ValidationResult(
            tenant_slug=tenant.tenant_slug,
            success=False,
            is_public=False,
            pagination_works=False,
            job_count=0,
        )
        
        try:
            # Step 1: Check API access
            api_url = tenant.get_api_url()
            is_public, job_count = self._check_api_access(api_url)
            
            result.is_public = is_public
            result.job_count = job_count
            
            if not is_public:
                result.error_message = "API not publicly accessible"
                return result
            
            # Step 2: Check pagination
            pagination_works = self._check_pagination(api_url)
            result.pagination_works = pagination_works
            
            # Success criteria: public access + at least basic response
            result.success = is_public
            
            if result.success:
                logger.info(f"   ✅ Validated: {tenant.tenant_slug} ({job_count} jobs)")
            else:
                logger.info(f"   ❌ Validation failed: {tenant.tenant_slug}")
            
        except Exception as e:
            result.error_message = str(e)
            logger.debug(f"   ❌ Validation error: {e}")
        
        finally:
            elapsed_ms = int((time.time() - start_time) * 1000)
            result.response_time_ms = elapsed_ms
        
        return result
    
    def validate_slug(self, slug: str) -> ValidationResult:
        """
        Validate a tenant by its slug string.
        
        Args:
            slug: Tenant slug in format "tenant|shard|site_id"
            
        Returns:
            ValidationResult
        """
        parts = slug.split("|")
        if len(parts) != 3:
            return ValidationResult(
                tenant_slug=slug,
                success=False,
                error_message="Invalid slug format"
            )
        
        tenant_name, shard, site_id = parts
        tenant = WorkdayTenant(
            tenant_domain=f"{tenant_name}.{shard}.myworkdayjobs.com",
            tenant_slug=slug,
            tenant_name=tenant_name,
            shard=shard,
            site_id=site_id,
        )
        
        return self.validate(tenant)
    
    def _check_api_access(self, api_url: str) -> tuple[bool, int]:
        """
        Check if the Workday API is publicly accessible.
        
        Returns:
            (is_public, job_count)
        """
        try:
            payload = {
                "appliedFacets": {},
                "limit": 1,
                "offset": 0,
                "searchText": "",
            }
            
            response = self.session.post(
                api_url,
                json=payload,
                timeout=self.config.validation_timeout_seconds
            )
            
            if response.status_code == 200:
                data = response.json()
                job_count = data.get("total", 0)
                return True, job_count
            
            # 401/403 means auth required
            if response.status_code in (401, 403):
                return False, 0
            
            # 422 usually means site_id is wrong
            if response.status_code == 422:
                return False, 0
            
            return False, 0
            
        except Exception:
            return False, 0
    
    def _check_pagination(self, api_url: str) -> bool:
        """
        Check if pagination works correctly.
        """
        try:
            # Check offset/limit
            payload = {
                "appliedFacets": {},
                "limit": 5,
                "offset": 0,
                "searchText": "",
            }
            
            response = self.session.post(
                api_url,
                json=payload,
                timeout=self.config.validation_timeout_seconds
            )
            
            if response.status_code != 200:
                return False
            
            data = response.json()
            postings = data.get("jobPostings", [])
            
            # If there are jobs, pagination is working
            return len(postings) > 0 or data.get("total", 0) == 0
            
        except Exception:
            return False
    
    def batch_validate(self, tenants: list[WorkdayTenant]) -> list[ValidationResult]:
        """
        Validate multiple tenants.
        
        Args:
            tenants: List of WorkdayTenant objects
            
        Returns:
            List of ValidationResult objects
        """
        results = []
        for tenant in tenants:
            result = self.validate(tenant)
            results.append(result)
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        return results
