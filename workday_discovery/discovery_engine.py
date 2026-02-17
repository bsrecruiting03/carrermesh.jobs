"""
Workday Tenant Discovery Engine

Main orchestrator that coordinates all discovery strategies.
"""

import os
import time
import random
import logging
from datetime import datetime
from typing import List, Optional, Set
import psycopg2

from .models import (
    WorkdayTenant, 
    DiscoveryConfig, 
    DiscoveryResult, 
    ValidationResult,
    TenantStatus,
    DiscoverySource,
)
from .crawlers import (
    CareerPageCrawler,
    SearchEngineSeeder,
    LinkFollower,
    CommunitySeedLoader,
)
from .validator import TenantValidator
from .registry import TenantRegistry

logger = logging.getLogger(__name__)


class WorkdayTenantDiscoveryEngine:
    """
    Main orchestrator for Workday tenant discovery.
    
    Coordinates multiple discovery strategies:
    1. Career Page Crawling
    2. Search Engine Seeding
    3. Link Following
    4. Community Seeding
    """
    
    def __init__(self, db_url: Optional[str] = None, config: Optional[DiscoveryConfig] = None):
        self.config = config or DiscoveryConfig()
        
        # Force correct URL to bypass config/env issues
        self.db_url = "postgresql://postgres:password@127.0.0.1:5433/job_board"
        
        # Initialize components
        self.career_crawler = CareerPageCrawler()
        self.search_seeder = SearchEngineSeeder(self.config)
        self.link_follower = LinkFollower()
        self.community_loader = CommunitySeedLoader()
        self.validator = TenantValidator(self.config)
        
        # Database connection (lazy init)
        self._conn = None
        self._registry = None
    
    @property
    def conn(self):
        if self._conn is None:
            self._conn = psycopg2.connect(self.db_url)
            self._conn.autocommit = True
        return self._conn
    
    @property
    def registry(self) -> TenantRegistry:
        if self._registry is None:
            self._registry = TenantRegistry(self.conn)
        return self._registry
    
    def run_discovery_cycle(
        self, 
        company_names: Optional[List[str]] = None,
        company_domains: Optional[List[dict]] = None,
        use_fortune500: bool = False,
        validate: bool = True,
        sync_to_companies: bool = True,
    ) -> DiscoveryResult:
        """
        Execute a full discovery cycle.
        
        Args:
            company_names: List of company names to discover
            company_domains: List of dicts with 'name' and 'domain'
            use_fortune500: Use Fortune 500 as source
            validate: Whether to validate discovered tenants
            sync_to_companies: Whether to sync validated tenants to companies table
            
        Returns:
            DiscoveryResult with statistics
        """
        start_time = time.time()
        result = DiscoveryResult(
            total_companies_processed=0,
            tenants_discovered=0,
            tenants_validated=0,
            tenants_failed=0,
            discovery_source_breakdown={},
        )
        
        logger.info("🚀 Starting Workday Tenant Discovery Cycle")
        
        # Build company list
        companies: List[dict] = []
        
        if company_names:
            companies.extend([{"name": n} for n in company_names])
        
        if company_domains:
            companies.extend(company_domains)
        
        if use_fortune500:
            fortune_companies = self.community_loader.get_fortune500_for_discovery()
            for fc in fortune_companies:
                companies.append({
                    "name": fc.get("name"),
                    "domain": fc.get("urls", {}).get("company_website"),
                })
        
        if not companies:
            logger.warning("No companies to process")
            return result
        
        # Batch processing
        total = len(companies)
        batch_size = self.config.batch_size
        discovered_tenants: List[WorkdayTenant] = []
        seen_slugs: Set[str] = set()
        
        for i in range(0, total, batch_size):
            batch = companies[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            logger.info(f"\n📦 Batch {batch_num}/{total_batches} ({len(batch)} companies)")
            
            for company in batch:
                name = company.get("name", "")
                domain = company.get("domain", "")
                
                result.total_companies_processed += 1
                
                try:
                    tenants = self._discover_for_company(name, domain)
                    
                    for tenant in tenants:
                        if tenant.tenant_slug not in seen_slugs:
                            discovered_tenants.append(tenant)
                            seen_slugs.add(tenant.tenant_slug)
                            result.tenants_discovered += 1
                            
                            # Track by source
                            source = tenant.discovery_source.value
                            result.discovery_source_breakdown[source] = \
                                result.discovery_source_breakdown.get(source, 0) + 1
                    
                except Exception as e:
                    result.errors.append(f"{name}: {str(e)}")
                    logger.error(f"   ❌ Error discovering {name}: {e}")
                
                # Rate limiting
                delay = random.randint(
                    self.config.delay_min_seconds,
                    self.config.delay_max_seconds
                )
                time.sleep(delay)
            
            # Check batch limit
            if batch_num >= self.config.max_batches_per_run:
                logger.info(f"⚠️ Max batches reached ({self.config.max_batches_per_run})")
                break
        
        logger.info(f"\n📊 Discovery complete: {result.tenants_discovered} tenants found")
        
        # Validation phase
        if validate and discovered_tenants:
            logger.info("\n🔍 Validating discovered tenants...")
            
            for tenant in discovered_tenants:
                # Save to registry first
                self.registry.upsert_tenant(tenant)
                
                # Validate
                validation = self.validator.validate(tenant)
                self.registry.update_validation_result(tenant.tenant_slug, validation)
                
                if validation.success:
                    result.tenants_validated += 1
                    
                    # Sync to companies table
                    if sync_to_companies:
                        self.registry.sync_to_companies_table(tenant.tenant_slug)
                else:
                    result.tenants_failed += 1
                
                time.sleep(0.5)  # Rate limit
        
        # Finalize
        result.duration_seconds = time.time() - start_time
        self._log_discovery_run(result)
        
        logger.info(f"\n✅ Discovery cycle complete in {result.duration_seconds:.1f}s")
        logger.info(f"   Discovered: {result.tenants_discovered}")
        logger.info(f"   Validated: {result.tenants_validated}")
        logger.info(f"   Failed: {result.tenants_failed}")
        
        return result
    
    def _discover_for_company(self, name: str, domain: Optional[str]) -> List[WorkdayTenant]:
        """
        Discover Workday tenants for a single company.
        Uses multiple strategies.
        """
        tenants: List[WorkdayTenant] = []
        seen_slugs: Set[str] = set()
        
        logger.info(f"🔍 Discovering: {name}")
        
        # Strategy 1: Career page crawling (if domain provided)
        if domain:
            try:
                crawled = self.career_crawler.crawl(domain, name)
                for tenant in crawled:
                    if tenant.tenant_slug not in seen_slugs:
                        tenants.append(tenant)
                        seen_slugs.add(tenant.tenant_slug)
            except Exception as e:
                logger.debug(f"   Career crawl failed: {e}")
        
        # Strategy 2: Search engine seeding
        if not tenants:
            try:
                searched = self.search_seeder.search(name, use_premium=False)
                for tenant in searched:
                    if tenant.tenant_slug not in seen_slugs:
                        tenants.append(tenant)
                        seen_slugs.add(tenant.tenant_slug)
            except Exception as e:
                logger.debug(f"   Search seeding failed: {e}")
        
        # Strategy 3: Link following (if we found tenants)
        if tenants:
            try:
                related = self.link_follower.follow_all_known_tenants(tenants)
                for tenant in related:
                    if tenant.tenant_slug not in seen_slugs:
                        tenants.append(tenant)
                        seen_slugs.add(tenant.tenant_slug)
            except Exception as e:
                logger.debug(f"   Link following failed: {e}")
        
        return tenants
    
    def import_existing_tenants(self) -> int:
        """
        Import existing Workday tenants from companies.json to the registry.
        
        Returns:
            Number of tenants imported
        """
        logger.info("📂 Importing existing Workday tenants from companies.json...")
        
        existing = self.community_loader.load_existing_tenants()
        imported = 0
        
        for tenant in existing:
            try:
                self.registry.upsert_tenant(tenant)
                imported += 1
            except Exception as e:
                logger.debug(f"Failed to import {tenant.tenant_slug}: {e}")
        
        logger.info(f"✅ Imported {imported} existing tenants")
        return imported
    
    def validate_existing_tenants(self, limit: int = 100) -> dict:
        """
        Validate existing tenants in the registry.
        
        Returns:
            Validation statistics
        """
        logger.info(f"🔍 Validating existing tenants (limit: {limit})...")
        
        tenants = self.registry.get_tenants_for_validation(limit)
        validated = 0
        failed = 0
        
        for tenant in tenants:
            result = self.validator.validate(tenant)
            self.registry.update_validation_result(tenant.tenant_slug, result)
            
            if result.success:
                validated += 1
                self.registry.sync_to_companies_table(tenant.tenant_slug)
            else:
                failed += 1
            
            time.sleep(0.5)
        
        return {
            "total_checked": len(tenants),
            "validated": validated,
            "failed": failed,
        }
    
    def get_statistics(self) -> dict:
        """Get discovery engine statistics."""
        registry_stats = self.registry.get_statistics()
        serpapi_stats = self.search_seeder.get_serpapi_usage()
        
        return {
            "registry": registry_stats,
            "serpapi": serpapi_stats,
        }
    
    def _log_discovery_run(self, result: DiscoveryResult):
        """Log a discovery run to the database."""
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO workday_discovery_log (
                        run_completed_at, companies_processed, tenants_discovered,
                        tenants_validated, tenants_failed, serpapi_calls_used,
                        errors, config_snapshot
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    datetime.utcnow(),
                    result.total_companies_processed,
                    result.tenants_discovered,
                    result.tenants_validated,
                    result.tenants_failed,
                    self.search_seeder.serpapi_calls_today,
                    "\n".join(result.errors) if result.errors else None,
                    None,  # Could add config JSON here
                ))
        except Exception as e:
            logger.debug(f"Failed to log discovery run: {e}")
    
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
