"""
Rebuild Search Projection
Syncs all jobs to the job_search denormalized table.
"""

import sys
import os
import logging
from tqdm import tqdm

# Add root project directory to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from us_ats_jobs.db import database
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rebuild_all(batch_size=1000):
    """Iterate through all jobs and upsert search projection."""
    conn = database.get_connection()
    # Close it, we just want to ensure pool is init
    
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM jobs")
            total = cur.fetchone()[0]
            logger.info(f"Total jobs to sync: {total}")
            
            cur.execute("SELECT job_id FROM jobs ORDER BY job_id")
            
            all_ids = []
            while True:
                rows = cur.fetchmany(batch_size)
                if not rows:
                    break
                
                job_ids = [r[0] for r in rows]
                # Ensure batch is unique to avoid sub-second collision in UPSERT
                job_ids = list(set(job_ids))
                database.upsert_job_search_projection(job_ids)
                
                processed = len(job_ids)
                all_ids.extend(job_ids)
                if len(all_ids) % 10000 == 0:
                     logger.info(f"Synced {len(all_ids)}/{total} jobs...")

    logger.info("Search projection rebuild complete!")

if __name__ == "__main__":
    rebuild_all()
