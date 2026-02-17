"""
Tenant Registry

Persistent storage layer for Workday tenants.
Links to the companies table for ingestion integration.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor

from .models import WorkdayTenant, TenantStatus, DiscoverySource, ValidationResult

logger = logging.getLogger(__name__)


class TenantRegistry:
    """
    Persistent registry for Workday tenants.
    
    Manages the workday_tenants table and syncs with companies table.
    """
    
    def __init__(self, db_conn):
        """
        Initialize the registry.
        
        Args:
            db_conn: PostgreSQL connection (from psycopg2)
        """
        self.conn = db_conn
    
    def upsert_tenant(self, tenant: WorkdayTenant) -> int:
        """
        Insert or update a tenant.
        
        Returns:
            tenant_id from the database
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO workday_tenants (
                    tenant_domain, tenant_slug, tenant_name, shard, site_id,
                    company_name, company_domain, status, discovery_source,
                    first_discovered_at, job_count_estimate, ingestion_priority
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tenant_slug) DO UPDATE SET
                    company_name = COALESCE(EXCLUDED.company_name, workday_tenants.company_name),
                    company_domain = COALESCE(EXCLUDED.company_domain, workday_tenants.company_domain),
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (
                tenant.tenant_domain,
                tenant.tenant_slug,
                tenant.tenant_name,
                tenant.shard,
                tenant.site_id,
                tenant.company_name,
                tenant.company_domain,
                tenant.status.value if tenant.status else TenantStatus.PENDING_VALIDATION.value,
                tenant.discovery_source.value if tenant.discovery_source else DiscoverySource.MANUAL.value,
                tenant.first_discovered_at or datetime.utcnow(),
                tenant.job_count_estimate,
                tenant.ingestion_priority,
            ))
            
            tenant_id = cur.fetchone()[0]
            self.conn.commit()
            return tenant_id
    
    def update_validation_result(self, tenant_slug: str, result: ValidationResult):
        """Update a tenant's validation status."""
        with self.conn.cursor() as cur:
            if result.success:
                cur.execute("""
                    UPDATE workday_tenants SET
                        status = 'active',
                        last_validated_at = %s,
                        job_count_estimate = %s,
                        validation_failures = 0,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE tenant_slug = %s
                """, (result.validated_at, result.job_count, tenant_slug))
            else:
                cur.execute("""
                    UPDATE workday_tenants SET
                        validation_failures = validation_failures + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE tenant_slug = %s
                """, (tenant_slug,))
                
                # Check if we should mark as inactive
                cur.execute("""
                    UPDATE workday_tenants SET
                        status = 'inactive'
                    WHERE tenant_slug = %s AND validation_failures >= 3
                """, (tenant_slug,))
            
            self.conn.commit()
    
    def get_tenant(self, tenant_slug: str) -> Optional[WorkdayTenant]:
        """Get a tenant by slug."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM workday_tenants WHERE tenant_slug = %s
            """, (tenant_slug,))
            row = cur.fetchone()
            
            if not row:
                return None
            
            return self._row_to_tenant(row)
    
    def get_active_tenants(self, limit: int = 1000) -> List[WorkdayTenant]:
        """Get all active tenants for ingestion."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM workday_tenants
                WHERE status = 'active'
                AND (circuit_open_until IS NULL OR circuit_open_until <= CURRENT_TIMESTAMP)
                ORDER BY ingestion_priority DESC, last_ingested_at ASC NULLS FIRST
                LIMIT %s
            """, (limit,))
            
            return [self._row_to_tenant(row) for row in cur.fetchall()]
    
    def get_tenants_for_validation(self, limit: int = 100) -> List[WorkdayTenant]:
        """Get tenants needing validation (weekly re-check)."""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM workday_tenants
                WHERE status IN ('pending_validation', 'inactive')
                OR (last_validated_at IS NULL)
                OR (last_validated_at < CURRENT_TIMESTAMP - INTERVAL '7 days')
                ORDER BY validation_failures ASC, first_discovered_at ASC
                LIMIT %s
            """, (limit,))
            
            return [self._row_to_tenant(row) for row in cur.fetchall()]
    
    def mark_inactive(self, tenant_id: int):
        """Mark a tenant as inactive."""
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE workday_tenants SET
                    status = 'inactive',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (tenant_id,))
            self.conn.commit()
    
    def record_ingestion(self, tenant_slug: str, jobs_found: int, success: bool):
        """Record an ingestion attempt."""
        with self.conn.cursor() as cur:
            if success:
                cur.execute("""
                    UPDATE workday_tenants SET
                        last_ingested_at = CURRENT_TIMESTAMP,
                        job_count_estimate = %s,
                        consecutive_failures = 0,
                        circuit_open_until = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE tenant_slug = %s
                """, (jobs_found, tenant_slug))
            else:
                cur.execute("""
                    UPDATE workday_tenants SET
                        consecutive_failures = consecutive_failures + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE tenant_slug = %s
                """, (tenant_slug,))
                
                # Open circuit breaker if too many failures
                cur.execute("""
                    UPDATE workday_tenants SET
                        circuit_open_until = CURRENT_TIMESTAMP + INTERVAL '7 days'
                    WHERE tenant_slug = %s AND consecutive_failures >= 3
                """, (tenant_slug,))
            
            self.conn.commit()
    
    def sync_to_companies_table(self, tenant_slug: str) -> Optional[int]:
        """
        Sync a validated tenant to the companies table for ingestion.
        
        Returns:
            company_id if successful
        """
        tenant = self.get_tenant(tenant_slug)
        if not tenant or tenant.status != TenantStatus.ACTIVE:
            return None
        
        with self.conn.cursor() as cur:
            # Check if company already exists
            cur.execute("""
                SELECT id FROM companies WHERE ats_url = %s
            """, (tenant.tenant_slug,))
            existing = cur.fetchone()
            
            if existing:
                company_id = existing[0]
                # Update the link
                cur.execute("""
                    UPDATE workday_tenants SET company_id = %s WHERE tenant_slug = %s
                """, (company_id, tenant_slug))
            else:
                # Insert new company
                cur.execute("""
                    INSERT INTO companies (name, ats_url, ats_provider, consecutive_failures)
                    VALUES (%s, %s, 'workday', 0)
                    RETURNING id
                """, (tenant.company_name or tenant.tenant_name, tenant.tenant_slug))
                company_id = cur.fetchone()[0]
                
                # Update the link
                cur.execute("""
                    UPDATE workday_tenants SET company_id = %s WHERE tenant_slug = %s
                """, (company_id, tenant_slug))
            
            self.conn.commit()
            return company_id
    
    def get_statistics(self) -> dict:
        """Get registry statistics."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'active') as active,
                    COUNT(*) FILTER (WHERE status = 'inactive') as inactive,
                    COUNT(*) FILTER (WHERE status = 'pending_validation') as pending,
                    COUNT(*) FILTER (WHERE company_id IS NOT NULL) as synced
                FROM workday_tenants
            """)
            row = cur.fetchone()
            
            cur.execute("""
                SELECT shard, COUNT(*) FROM workday_tenants GROUP BY shard ORDER BY COUNT(*) DESC
            """)
            shards = {r[0]: r[1] for r in cur.fetchall()}
            
            return {
                "total": row[0],
                "active": row[1],
                "inactive": row[2],
                "pending_validation": row[3],
                "synced_to_companies": row[4],
                "by_shard": shards,
            }
    
    def _row_to_tenant(self, row: dict) -> WorkdayTenant:
        """Convert a database row to a WorkdayTenant object."""
        return WorkdayTenant(
            id=row.get("id"),
            company_id=row.get("company_id"),
            tenant_domain=row["tenant_domain"],
            tenant_slug=row["tenant_slug"],
            tenant_name=row["tenant_name"],
            shard=row["shard"],
            site_id=row["site_id"],
            company_name=row.get("company_name"),
            company_domain=row.get("company_domain"),
            status=TenantStatus(row.get("status", "pending_validation")),
            discovery_source=DiscoverySource(row.get("discovery_source", "manual")),
            first_discovered_at=row.get("first_discovered_at"),
            last_validated_at=row.get("last_validated_at"),
            last_ingested_at=row.get("last_ingested_at"),
            job_count_estimate=row.get("job_count_estimate", 0),
            ingestion_priority=row.get("ingestion_priority", 5),
            validation_failures=row.get("validation_failures", 0),
            consecutive_failures=row.get("consecutive_failures", 0),
            circuit_open_until=row.get("circuit_open_until"),
        )
