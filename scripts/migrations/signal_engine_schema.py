"""
Phase 13: Database Migration for Signal-Based Discovery Engine

Creates:
1. domain_graph table - Logs ALL outbound domains from job data
2. workday_signal_scanned column on raw_jobs - Tracks processing state

NON-DESTRUCTIVE: No existing data is modified or deleted.
"""

import psycopg2
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SignalEngineMigration")

DATABASE_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

def run_migration():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    logger.info("🔧 Starting Signal-Based Discovery Engine Migration...")
    
    # 1. Create domain_graph table
    logger.info("   [1/3] Creating domain_graph table...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS domain_graph (
            id SERIAL PRIMARY KEY,
            source_job_id TEXT,
            source_endpoint_id INTEGER,
            raw_url TEXT NOT NULL,
            normalized_domain TEXT NOT NULL,
            ats_hint TEXT,  -- Optional: 'workday', 'greenhouse', etc.
            first_seen_at TIMESTAMP DEFAULT NOW(),
            
            -- Indexes for efficient querying
            CONSTRAINT unique_job_url UNIQUE (source_job_id, raw_url)
        );
        
        -- Index for domain clustering analysis
        CREATE INDEX IF NOT EXISTS idx_domain_graph_domain ON domain_graph(normalized_domain);
        CREATE INDEX IF NOT EXISTS idx_domain_graph_ats_hint ON domain_graph(ats_hint);
    """)
    logger.info("   ✅ domain_graph table created")
    
    # 2. Add workday_signal_scanned column to raw_jobs (SAFE FLAG)
    logger.info("   [2/3] Adding workday_signal_scanned column to raw_jobs...")
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'raw_jobs' AND column_name = 'workday_signal_scanned'
            ) THEN
                ALTER TABLE raw_jobs ADD COLUMN workday_signal_scanned BOOLEAN DEFAULT FALSE;
                CREATE INDEX IF NOT EXISTS idx_raw_jobs_signal_scanned ON raw_jobs(workday_signal_scanned);
            END IF;
        END $$;
    """)
    logger.info("   ✅ workday_signal_scanned column added")
    
    # 3. Verify existing fields in career_endpoints (reuse, don't add duplicates)
    logger.info("   [3/3] Verifying career_endpoints schema...")
    cur.execute("""
        DO $$
        BEGIN
            -- confidence_score (may exist)
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'career_endpoints' AND column_name = 'confidence_score'
            ) THEN
                ALTER TABLE career_endpoints ADD COLUMN confidence_score FLOAT DEFAULT 0.5;
            END IF;
            
            -- last_verified_at (may exist)
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'career_endpoints' AND column_name = 'last_verified_at'
            ) THEN
                ALTER TABLE career_endpoints ADD COLUMN last_verified_at TIMESTAMP;
            END IF;
            
            -- discovery_source already exists as discovered_from, skip
        END $$;
    """)
    logger.info("   ✅ career_endpoints schema verified")
    
    conn.commit()
    
    # Report stats
    cur.execute("SELECT COUNT(*) FROM raw_jobs")
    raw_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM raw_jobs WHERE workday_signal_scanned = FALSE")
    pending_count = cur.fetchone()[0]
    
    logger.info(f"📊 Migration Complete:")
    logger.info(f"   - Total raw_jobs: {raw_count}")
    logger.info(f"   - Pending signal scan: {pending_count}")
    
    conn.close()
    return True

if __name__ == "__main__":
    run_migration()
