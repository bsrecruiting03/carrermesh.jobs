import sys
import os
import logging

# Add root project directory to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from us_ats_jobs.db import database
from us_ats_jobs.intelligence.skills_db import SkillExtractorDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DebugExtraction")

def debug_job(job_id):
    db_config = database.get_db_config()
    extractor = SkillExtractorDB(db_config)
    
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT job_description, title FROM jobs WHERE job_id = %s", (job_id,))
            row = cur.fetchone()
            if not row:
                print("Job not found")
                return
            
            description, title = row
            print(f"Testing Job: {job_id}")
            print(f"Title: {title}")
            print(f"Description length: {len(description or '')}")
            
            import time
            start = time.time()
            skills = extractor.extract(description)
            duration = time.time() - start
            
            print(f"Extraction took {duration:.2f} seconds")
            print(f"Found {len(skills)} skills: {[s.canonical_name for s in skills]}")

if __name__ == "__main__":
    debug_job("ashby_66dd0b81-12a6-430a-9810-c0ee0fb3f323")
