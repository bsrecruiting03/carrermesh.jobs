"""
Deduplicate Companies
Safely merges companies with duplicate names.
Fixes Career Endpoints and Workday Tenants links first.
"""

import sys
import os
import logging

# Add root project directory to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from us_ats_jobs.db import database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def dedupe():
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Find duplicate pairs/groups
            cur.execute("""
                SELECT name, array_agg(id ORDER BY id DESC) as ids
                FROM companies
                GROUP BY name
                HAVING count(*) > 1
            """)
            
            duplicates = cur.fetchall()
            logger.info(f"Found {len(duplicates)} duplicate company names to merge.")
            
            for name, ids in duplicates:
                keep_id = ids[0]
                drop_ids = ids[1:]
                
                logger.info(f"Merging '{name}': keeping {keep_id}, dropping {drop_ids}")
                
                # Update referencing tables
                for drop_id in drop_ids:
                    cur.execute("UPDATE career_endpoints SET company_id = %s WHERE company_id = %s", (keep_id, drop_id))
                    cur.execute("UPDATE workday_tenants SET company_id = %s WHERE company_id = %s", (keep_id, drop_id))
                
                # Delete old ones
                cur.execute("DELETE FROM companies WHERE id = ANY(%s)", (drop_ids,))
                
            conn.commit()
    logger.info("Deduplication complete!")

if __name__ == "__main__":
    dedupe()
