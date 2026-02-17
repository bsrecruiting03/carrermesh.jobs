"""
Community Seeder

Loads seed data from community sources and existing datasets
for initial tenant discovery.
"""

import os
import json
import logging
from typing import List, Set, Optional
from pathlib import Path

from ..models import WorkdayTenant, DiscoverySource

logger = logging.getLogger(__name__)


class CommunitySeedLoader:
    """
    Strategy 4: Community & Public List Seeding
    
    Seed initial tenant list from:
    - Existing companies.json (2000+ Workday tenants)
    - Fortune 500 companies for discovery
    - GitHub repos / open datasets (future)
    """
    
    def __init__(self, project_root: Optional[str] = None):
        if project_root is None:
            # Auto-detect project root
            current_file = Path(__file__).resolve()
            self.project_root = current_file.parent.parent.parent
        else:
            self.project_root = Path(project_root)
    
    def load_existing_workday_slugs(self) -> List[str]:
        """
        Load existing Workday slugs from companies.json.
        
        Returns:
            List of tenant slugs in format "tenant|shard|site_id"
        """
        companies_file = self.project_root / "companies.json"
        
        if not companies_file.exists():
            logger.warning(f"companies.json not found at {companies_file}")
            return []
        
        try:
            with open(companies_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Workday tenants are stored in the "workday" key
            workday_slugs = data.get("workday", [])
            logger.info(f"📂 Loaded {len(workday_slugs)} existing Workday slugs from companies.json")
            return workday_slugs
            
        except Exception as e:
            logger.error(f"Failed to load companies.json: {e}")
            return []
    
    def load_existing_tenants(self) -> List[WorkdayTenant]:
        """
        Load existing Workday tenants as WorkdayTenant objects.
        
        Returns:
            List of WorkdayTenant objects from existing data
        """
        slugs = self.load_existing_workday_slugs()
        tenants: List[WorkdayTenant] = []
        
        for slug in slugs:
            tenant = self._parse_slug(slug)
            if tenant:
                tenant.discovery_source = DiscoverySource.COMMUNITY_SEED
                tenants.append(tenant)
        
        return tenants
    
    def _parse_slug(self, slug: str) -> Optional[WorkdayTenant]:
        """Parse a tenant slug into a WorkdayTenant object."""
        try:
            parts = slug.split("|")
            if len(parts) != 3:
                return None
            
            tenant_name, shard, site_id = parts
            tenant_domain = f"{tenant_name}.{shard}.myworkdayjobs.com"
            
            return WorkdayTenant(
                tenant_domain=tenant_domain,
                tenant_slug=slug,
                tenant_name=tenant_name,
                shard=shard,
                site_id=site_id,
            )
        except Exception:
            return None
    
    def load_fortune500_companies(self) -> List[dict]:
        """
        Load Fortune 500 companies for discovery targeting.
        
        Returns:
            List of company dicts with name, website, careers_page
        """
        fortune_file = self.project_root / "fortune500_restructured.json"
        
        if not fortune_file.exists():
            logger.warning(f"fortune500_restructured.json not found at {fortune_file}")
            return []
        
        try:
            with open(fortune_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            companies = data.get("companies", [])
            logger.info(f"📂 Loaded {len(companies)} Fortune 500 companies")
            return companies
            
        except Exception as e:
            logger.error(f"Failed to load fortune500_restructured.json: {e}")
            return []
    
    def get_fortune500_for_discovery(self) -> List[dict]:
        """
        Get Fortune 500 companies that aren't already known Workday tenants.
        
        Returns:
            List of companies to target for Workday discovery
        """
        fortune_companies = self.load_fortune500_companies()
        existing_slugs = set(self.load_existing_workday_slugs())
        existing_names = set()
        
        # Extract company names from existing slugs
        for slug in existing_slugs:
            parts = slug.split("|")
            if parts:
                existing_names.add(parts[0].lower())
        
        # Filter to companies not already known
        candidates = []
        for company in fortune_companies:
            name = company.get("name", "")
            # Simple name matching (could be improved with fuzzy matching)
            name_lower = name.lower().replace(" ", "").replace("-", "").replace(".", "")
            
            # Check if any existing slug starts with this name
            is_known = any(name_lower in slug.lower() for slug in existing_names)
            
            if not is_known:
                candidates.append(company)
        
        logger.info(f"📊 {len(candidates)} Fortune 500 companies not yet discovered for Workday")
        return candidates
    
    def load_seed_companies(self, include_fortune500: bool = True) -> List[str]:
        """
        Load company names for discovery seeding.
        
        Args:
            include_fortune500: Include Fortune 500 companies
            
        Returns:
            List of company names to target for discovery
        """
        companies: Set[str] = set()
        
        if include_fortune500:
            for company in self.get_fortune500_for_discovery():
                name = company.get("name")
                if name:
                    companies.add(name)
        
        return list(companies)
    
    def get_companies_by_ats_platform(self, platform: str = "Custom") -> List[dict]:
        """
        Get Fortune 500 companies with a specific ATS platform.
        
        Custom platform companies are good candidates for Workday discovery.
        """
        fortune_companies = self.load_fortune500_companies()
        
        return [
            c for c in fortune_companies
            if c.get("careers", {}).get("platform") == platform
        ]
