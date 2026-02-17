import sys
import os
import logging
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import meilisearch
from datetime import datetime, date

# Add root to python path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
PG_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@127.0.0.1:5433/job_board")
MEILI_URL = os.getenv("MEILI_URL", "http://127.0.0.1:7700")
MEILI_KEY = os.getenv("MEILI_MASTER_KEY", "masterKey")

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SYNC] - %(levelname)s - %(message)s')
logger = logging.getLogger("MeiliSync")

def get_db_connection():
    try:
        return psycopg2.connect(PG_URL)
    except Exception as e:
        logger.error(f"❌ Postgres Connection Failed: {e}")
        sys.exit(1)

def get_last_sync_time(conn):
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT (value->>'timestamp') FROM system_metadata WHERE key = 'meilisearch_last_sync'")
            row = cur.fetchone()
            if row and row[0]:
                return datetime.fromisoformat(row[0])
    except Exception as e:
        logger.warning(f"Could not fetch last sync time: {e}")
    return None

def set_last_sync_time(conn, timestamp):
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO system_metadata (key, value)
                VALUES ('meilisearch_last_sync', jsonb_build_object('timestamp', %s::text))
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()
            """, (timestamp.isoformat(),))
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to update sync timestamp: {e}")

def transform_job(job):
    """
    Transforms a Postgres job row into a Meilisearch document.
    Handles date conversion and cleaning.
    """
    # 1. Dates: Convert datetime to timestamp (int) or ISO string
    # Meilisearch sorts strings well or numbers. ISO8601 is best for readability.
    if isinstance(job.get('date_posted'), datetime):
        job['date_posted'] = job['date_posted'].isoformat()
    
    if isinstance(job.get('ingested_at'), datetime):
        job['ingested_at'] = job['ingested_at'].isoformat()
        
    # 2. Tech Stack: postgres returns comma-separated string if simple query, 
    # or we might need to join with enrichment.
    # The query below fetches from enrichment table, so we handle it there.
    if job.get('tech_languages'):
        job['tech_languages'] = [s.strip() for s in job['tech_languages'].split(',')]
    
    # 3. Geo: Create _geo object if we had lat/lng (we don't currently)
    
    return job

def sync_jobs():
    logger.info("🚀 Starting Meilisearch Sync...")
    
    # 1. Connect Meilisearch
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        index = client.index('jobs')
        logger.info(f"✅ Connected to Meilisearch at {MEILI_URL}")
    except Exception as e:
        logger.error(f"❌ Meilisearch Connection Failed: {e}")
        return

    # 2. Configure Index (Run once/idempotent)
    logger.info("⚙️  Configuring Index Settings...")
    index.update_settings({
        'searchableAttributes': [
            'title',
            'company',
            'skills',
            'tech_languages',
            'tech_frameworks',
            'tech_tools',
            'specializations',
            'job_description',
            'job_summary',
            'normalized_location',
            'location'
        ],
        'filterableAttributes': [
            'is_remote',
            'work_mode',
            'seniority',
            'salary_min',
            'salary_max',
            'visa_sponsorship',
            'posted_bucket',
            'location',
            'city',
            'country',
            'normalized_location',
            'employment_type',
            'skills',
            'company',
            'department',
            'tech_languages',
            'tech_frameworks',
            'tech_tools',
            'tech_cloud',
            'tech_data',
            'specializations'
        ],
        'sortableAttributes': [
            'date_posted',
            'salary_max',
            'ingested_at'
        ],
        'rankingRules': [
            'words',
            'typo',
            'proximity',
            'attribute',
            'sort',
            'exactness'
        ]
    })
    
    # 3. Fetch Data
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Check for Incremental Sync
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Run full sync instead of incremental")
    args, unknown = parser.parse_known_args()

    last_sync = None if args.full else get_last_sync_time(conn)
    current_sync_start = datetime.now()

    if last_sync:
        logger.info(f"🔄 Running Incremental Sync (Since: {last_sync})")
    else:
        logger.info("⚡ Running Full Sync")

    BATCH_SIZE = 5000
    offset = 0
    total_synced = 0
    
    while True:
        # Join Jobs + Enrichment + Companies for full search power
        # For incremental, we look for jobs enriched or ingested AFTER last sync
        if last_sync:
            query = """
                SELECT 
                    j.job_id, j.title, j.company, j.location, j.city, j.country, j.normalized_location,
                    j.is_remote, j.work_mode, j.seniority, j.posted_bucket,
                    j.salary_min, j.salary_max, j.salary_currency,
                    j.visa_sponsorship, j.date_posted, j.job_link, j.ingested_at,
                    e.tech_languages, e.tech_frameworks, e.tech_tools, e.tech_cloud, e.tech_data,
                    e.job_summary, e.employment_type,
                    e.skill_ids, e.concept_ids,
                    c.logo_url
                FROM jobs j
                LEFT JOIN job_enrichment e ON j.job_id = e.job_id
                LEFT JOIN companies c ON j.company = c.name
                WHERE e.enriched_at > %s OR j.ingested_at > %s
                ORDER BY j.date_posted DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, (last_sync, last_sync, BATCH_SIZE, offset))
        else:
            query = """
                SELECT 
                    j.job_id, j.title, j.company, j.location, j.city, j.country, j.normalized_location,
                    j.is_remote, j.work_mode, j.seniority, j.posted_bucket,
                    j.salary_min, j.salary_max, j.salary_currency,
                    j.visa_sponsorship, j.date_posted, j.job_link, j.ingested_at,
                    e.tech_languages, e.tech_frameworks, e.tech_tools, e.tech_cloud, e.tech_data,
                    e.job_summary, e.employment_type,
                    e.skill_ids, e.concept_ids,
                    c.logo_url
                FROM jobs j
                LEFT JOIN job_enrichment e ON j.job_id = e.job_id
                LEFT JOIN companies c ON j.company = c.name
                ORDER BY j.date_posted DESC
                LIMIT %s OFFSET %s
            """
            cursor.execute(query, (BATCH_SIZE, offset))
        
        rows = cursor.fetchall()
        
        if not rows:
            break
            
        # Transform
        documents = []
        for row in rows:
            doc = dict(row)
            
            # Dates
            if isinstance(doc.get('date_posted'), (datetime, date)):
                doc['date_posted'] = doc['date_posted'].isoformat()
            if isinstance(doc.get('ingested_at'), (datetime, date)):
                doc['ingested_at'] = doc['ingested_at'].isoformat()
                
            # Skills Aggregation
            skills = []
            for field in ['tech_languages', 'tech_frameworks', 'tech_tools', 'tech_cloud', 'tech_data']:
                if doc.get(field):
                    # Postgres returns string "A, B, C" or sometimes list if we used array agg?
                    # Check schema: job_enrichment tech_ columns are TEXT.
                    val = doc.get(field)
                    if isinstance(val, str):
                        skills.extend([s.strip() for s in val.split(',') if s.strip()])
            
            doc['skills'] = list(set(skills)) # Dedupe
            doc['tech_stack'] = doc['skills'] # Backwards compatibility with frontend/api
            
            # Legacy tech_ fields as arrays for specific filtering
            if doc.get('tech_languages') and isinstance(doc['tech_languages'], str):
                doc['tech_languages'] = [s.strip() for s in doc['tech_languages'].split(',')]
            if doc.get('tech_frameworks') and isinstance(doc['tech_frameworks'], str):
                doc['tech_frameworks'] = [s.strip() for s in doc['tech_frameworks'].split(',')]
            if doc.get('tech_cloud') and isinstance(doc['tech_cloud'], str):
                doc['tech_cloud'] = [s.strip() for s in doc['tech_cloud'].split(',')]
            
            # Normalized IDs
            doc['skill_ids'] = doc.get('skill_ids') or []
            doc['concept_ids'] = doc.get('concept_ids') or []
            
            # Create a safe primary key for Meilisearch (alphanumeric, -, _)
            # job_id often contains / or . which Meili rejects as primary key
            doc['id'] = doc['job_id'].replace('/', '_').replace('.', '_').replace(':', '_')
            
            documents.append(doc)
        
        # Upsert
        try:
            task = index.add_documents(documents, primary_key='id')
            total_synced += len(documents)
            offset += BATCH_SIZE
            if total_synced % 5000 == 0:
                 logger.info(f"⏳ Synced {total_synced} jobs...")
        except Exception as e:
            logger.error(f"❌ Failed to sync batch: {e}")
            
    if total_synced > 0:
        set_last_sync_time(conn, current_sync_start)
    
    conn.close()
    logger.info(f"🎉 Sync Complete! Total Documents: {total_synced}")

if __name__ == "__main__":
    sync_jobs()
