import sys
import os
import logging
import uuid
import time

# Add root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from us_ats_jobs.db import database
from us_ats_jobs import worker_enrichment

# Setup logging
logging.basicConfig(level=logging.INFO)

def debug_polling():
    job_id = f"debug_test_{uuid.uuid4().hex[:6]}"
    print(f"DEBUG: Inserting job {job_id}...")
    
    # Cleaning up just in case
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM job_enrichment WHERE job_id = %s", (job_id,))
            cur.execute("DELETE FROM jobs WHERE job_id = %s", (job_id,))
    
    database.insert_jobs([{
        "job_id": job_id,
        "title": "Debug Job",
        "company": "Debug Corp",
        "job_description": "We need Python and SQL.",
        "location": "Remote",
        "date_posted": "2025-01-01"
    }])
    
    # Check if inserted
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT job_id FROM jobs WHERE job_id = %s", (job_id,))
            row = cur.fetchone()
            print(f"DEBUG: Job in DB: {row}")
            
            cur.execute("SELECT * FROM job_enrichment WHERE job_id = %s", (job_id,))
            row_enrich = cur.fetchone()
            print(f"DEBUG: Enrichment row exists: {row_enrich is not None}")

    print("DEBUG: Calling get_unenriched_jobs...")
    jobs = database.get_unenriched_jobs(limit=10)
    print(f"DEBUG: Returned {len(jobs)} jobs.")
    
    found = any(j['job_id'] == job_id for j in jobs)
    print(f"DEBUG: Found our job? {found}")
    
    if not found:
        print("❌ Polling failed. Dumping first 5 jobs returned:")
        for j in jobs[:5]:
            print(f"   - {j['job_id']}")
    else:
        print("✅ Polling works.")
        
        # Test Helper - Process Batch
        print("DEBUG: Running process_batch...")
        count = worker_enrichment.process_batch()
        print(f"DEBUG: Processed {count} jobs.")
        
        with database.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT tech_languages FROM job_enrichment WHERE job_id = %s", (job_id,))
                res = cur.fetchone()
                print(f"DEBUG: Enriched Result: {res}")

if __name__ == "__main__":
    from us_ats_jobs.db.database import init_pool
    init_pool()
    debug_polling()
