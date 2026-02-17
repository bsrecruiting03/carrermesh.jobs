
import sys
import os
import psycopg2
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))

from api.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_search_layer():
    conn = None
    try:
        logger.info("Connecting to database...")
        conn = psycopg2.connect(settings.database_url)
        conn.autocommit = True
        cur = conn.cursor()

        # --- STEP 1: CREATE SEARCH PROJECTION TABLE ---
        logger.info("STEP 1: Creating JOB_SEARCH table...")
        
        # We drop if exists to ensure we match the EXACT definition provided
        cur.execute("DROP TABLE IF EXISTS job_search CASCADE;")
        
        cur.execute("""
            CREATE TABLE job_search (
                job_id TEXT PRIMARY KEY,
                company_id TEXT NOT NULL,
                title TEXT NOT NULL,
                location TEXT,
                work_mode TEXT,
                experience_min INTEGER,
                experience_max INTEGER,
                tech_stack_text TEXT,
                job_summary TEXT,
                date_posted TIMESTAMP,
                is_active BOOLEAN NOT NULL,
                search_vector TSVECTOR
            );
        """)
        logger.info("✅ JOB_SEARCH table created.")

        # --- STEP 2: POPULATE DATA DETERMINISTICALLY ---
        logger.info("STEP 2: Populating data from JOBS and JOB_ENRICHMENT...")
        
        # Explicit JOINs as requested
        cur.execute("""
            INSERT INTO job_search (
                job_id,
                company_id,
                title,
                location,
                work_mode,
                experience_min,
                experience_max,
                tech_stack_text,
                job_summary,
                date_posted,
                is_active
            )
            SELECT
                j.job_id,
                j.company,
                j.title,
                j.location,
                j.work_mode,  -- Corrected: work_mode is in JOBS table
                je.experience_min,
                je.experience_max,
                
                -- Concatenate tech fields for full text search
                TRIM(CONCAT_WS(' ', 
                    je.tech_languages, 
                    je.tech_frameworks, 
                    je.tech_cloud, 
                    je.tech_tools, 
                    je.tech_data
                )) as tech_stack_text,
                
                je.job_summary,
                j.date_posted,
                TRUE -- Default to true as JOBS table doesn't have active status column yet
            FROM jobs j
            LEFT JOIN job_enrichment je ON je.job_id = j.job_id;
        """)
        
        row_count = cur.rowcount
        logger.info(f"✅ Populated {row_count} rows.")

        # --- STEP 3: BUILD SEARCH VECTOR (NO RUNTIME COMPUTATION) ---
        logger.info("STEP 3: Computing search vectors...")
        
        cur.execute("""
            UPDATE job_search
            SET search_vector =
                setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(tech_stack_text, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(job_summary, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(location, '')), 'C');
        """)
        logger.info("✅ Search vectors computed.")

        # --- STEP 4: INDEXING (MANDATORY) ---
        logger.info("STEP 4: Creating Indexes...")
        
        cur.execute("""
            CREATE INDEX job_search_fts_idx
            ON job_search
            USING GIN (search_vector);
        """)
        
        cur.execute("""
            CREATE INDEX job_search_active_idx
            ON job_search (is_active);
        """)
        logger.info("✅ Indexes created.")

        logger.info("🎉 Search Projection Layer setup complete.")

    except Exception as e:
        logger.error(f"❌ Failed to setup search layer: {e}")
        raise
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    setup_search_layer()
