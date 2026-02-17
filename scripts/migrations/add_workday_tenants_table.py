"""
Database migration: Add workday_tenants table.

This table tracks Workday tenant discovery and validation metadata,
linked to the companies table for ingestion.
"""

import os
import sys
import psycopg2
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.config import settings

# DB_URL = settings.database_url
DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"


def run_migration():
    """Create the workday_tenants table."""
    
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    
    try:
        with conn.cursor() as cur:
            print("🔧 Creating workday_tenants table...")
            
            # Main table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS workday_tenants (
                    id SERIAL PRIMARY KEY,
                    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
                    
                    -- Core identifiers
                    tenant_domain TEXT UNIQUE NOT NULL,
                    tenant_slug TEXT UNIQUE NOT NULL,
                    tenant_name TEXT NOT NULL,
                    shard TEXT NOT NULL,
                    site_id TEXT NOT NULL,
                    
                    -- Company metadata
                    company_name TEXT,
                    company_domain TEXT,
                    
                    -- Status
                    status TEXT DEFAULT 'pending_validation',
                    discovery_source TEXT DEFAULT 'manual',
                    
                    -- Timestamps
                    first_discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_validated_at TIMESTAMP,
                    last_ingested_at TIMESTAMP,
                    
                    -- Metrics
                    job_count_estimate INTEGER DEFAULT 0,
                    ingestion_priority INTEGER DEFAULT 5,
                    validation_failures INTEGER DEFAULT 0,
                    consecutive_failures INTEGER DEFAULT 0,
                    
                    -- Circuit breaker
                    circuit_open_until TIMESTAMP,
                    
                    -- Audit
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            print("   ✅ Table created")
            
            # Indexes
            print("🔧 Creating indexes...")
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_workday_tenants_status 
                ON workday_tenants(status);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_workday_tenants_priority 
                ON workday_tenants(ingestion_priority DESC);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_workday_tenants_last_ingested 
                ON workday_tenants(last_ingested_at);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_workday_tenants_company_id 
                ON workday_tenants(company_id);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_workday_tenants_shard 
                ON workday_tenants(shard);
            """)
            
            print("   ✅ Indexes created")
            
            # Discovery log table for tracking discovery runs
            print("🔧 Creating discovery_log table...")
            
            cur.execute("""
                CREATE TABLE IF NOT EXISTS workday_discovery_log (
                    id SERIAL PRIMARY KEY,
                    run_started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    run_completed_at TIMESTAMP,
                    companies_processed INTEGER DEFAULT 0,
                    tenants_discovered INTEGER DEFAULT 0,
                    tenants_validated INTEGER DEFAULT 0,
                    tenants_failed INTEGER DEFAULT 0,
                    serpapi_calls_used INTEGER DEFAULT 0,
                    errors TEXT,
                    config_snapshot JSONB
                );
            """)
            print("   ✅ Discovery log table created")
            
            # Get counts
            cur.execute("SELECT COUNT(*) FROM workday_tenants")
            tenant_count = cur.fetchone()[0]
            
            print(f"\n📊 Migration complete!")
            print(f"   Workday tenants in registry: {tenant_count}")
            
    finally:
        conn.close()


def rollback_migration():
    """Drop the workday_tenants table (for development only)."""
    
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    
    try:
        with conn.cursor() as cur:
            print("⚠️  Rolling back migration...")
            cur.execute("DROP TABLE IF EXISTS workday_discovery_log CASCADE")
            cur.execute("DROP TABLE IF EXISTS workday_tenants CASCADE")
            print("   ✅ Tables dropped")
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Workday tenants table migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback migration")
    args = parser.parse_args()
    
    if args.rollback:
        confirm = input("⚠️  This will DROP all Workday tenant data. Type 'yes' to confirm: ")
        if confirm.lower() == "yes":
            rollback_migration()
        else:
            print("Cancelled.")
    else:
        run_migration()
