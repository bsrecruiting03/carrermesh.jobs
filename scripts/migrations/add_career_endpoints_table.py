"""
Database migration: Add career_endpoints table.

This is the foundation for the Endpoint-Driven Architecture.
All job discovery and ingestion will pivot to use this table.
"""

import os
import sys
import psycopg2

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Force correct DB URL for local environment
DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"


def run_migration():
    """Create the career_endpoints table."""
    
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    
    try:
        with conn.cursor() as cur:
            print("🔧 Creating career_endpoints table...")
            
            # Main table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS career_endpoints (
                    id SERIAL PRIMARY KEY,
                    
                    -- Core Identity
                    canonical_url TEXT UNIQUE NOT NULL, -- The source of truth
                    ats_provider TEXT NOT NULL,         -- greenhouse, lever, workday, etc
                    ats_slug TEXT,                      -- e.g., 'stripe' or 'stripe.wd5' (optional if URL is enough)
                    
                    -- Status
                    active BOOLEAN DEFAULT TRUE,
                    verification_status TEXT DEFAULT 'pending_verification', -- pending, verified, failed
                    confidence_score FLOAT DEFAULT 0.0,
                    
                    -- Discovery Metadata
                    discovered_from TEXT DEFAULT 'manual', -- 'migration', 'link_mining', 'search', etc.
                    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_verified_at TIMESTAMP,
                    last_ingested_at TIMESTAMP,
                    
                    -- Metrics
                    consecutive_failures INTEGER DEFAULT 0,
                    last_failure_reason TEXT,
                    
                    -- Audit
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            print("   ✅ Table created")
            
            # Indexes
            print("🔧 Creating indexes...")
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_endpoints_active 
                ON career_endpoints(active);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_endpoints_provider 
                ON career_endpoints(ats_provider);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_endpoints_verification 
                ON career_endpoints(verification_status);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_endpoints_last_ingested 
                ON career_endpoints(last_ingested_at);
            """)
            
            print("   ✅ Indexes created")
            
            # Get counts
            cur.execute("SELECT COUNT(*) FROM career_endpoints")
            count = cur.fetchone()[0]
            
            print(f"\n📊 Migration complete!")
            print(f"   Career Endpoints: {count}")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


def rollback_migration():
    """Drop the career_endpoints table (for development only)."""
    
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    
    try:
        with conn.cursor() as cur:
            print("⚠️  Rolling back migration...")
            cur.execute("DROP TABLE IF EXISTS career_endpoints CASCADE")
            print("   ✅ Table dropped")
    finally:
        conn.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Career Endpoints table migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback migration")
    args = parser.parse_args()
    
    if args.rollback:
        confirm = input("⚠️  This will DROP all career_endpoints data. Type 'yes' to confirm: ")
        if confirm.lower() == "yes":
            rollback_migration()
        else:
            print("Cancelled.")
    else:
        run_migration()
