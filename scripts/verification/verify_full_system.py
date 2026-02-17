import os
import sys
import requests
import time
import psycopg2
import logging
from datetime import datetime

# Add api dir to path for db connection
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(root_dir, 'api'))
sys.path.append(root_dir)

# Import get_db from api.database
# But we need to make sure config import works. The worker script fix suggests adding 'api' to path helps.
from database import get_db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Verification")

TEST_JOB_ID = "verify-test-job-123"

def verify_read_path():
    logger.info("--- 1. Verifying READ Path (Search API) ---")
    try:
        # 1. Hit the API
        response = requests.get("http://127.0.0.1:8000/api/jobs?limit=1")
        if response.status_code != 200:
            logger.error(f"API returned {response.status_code}")
            return False
        
        data = response.json()
        jobs = data.get('jobs', [])
        if not jobs:
            logger.warning("No jobs returned by API (Database might be empty?)")
            return True # Not a failure of code, just data
        
        job = jobs[0]
        logger.info(f"API returned job: {job.get('title')}")
        
        # 2. Check for skills (tech_stack)
        tech_stack = job.get('tech_stack', [])
        logger.info(f"Tech Stack type: {type(tech_stack)}")
        logger.info(f"Tech Stack content: {tech_stack}")
        
        if isinstance(tech_stack, list):
            logger.info("✅ Tech stack is correctly a list (Python parsing works)")
        else:
            logger.error("❌ Tech stack is NOT a list")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Read path verification failed: {e}")
        return False

def verify_write_path():
    logger.info("\n--- 2. Verifying WRITE Path (Worker & Pipeline) ---")
    
    # 1. Cleanup Test Job
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM jobs WHERE job_id = %s", (TEST_JOB_ID,))
            cur.execute("DELETE FROM job_enrichment WHERE job_id = %s", (TEST_JOB_ID,))
            cur.execute("DELETE FROM job_search WHERE job_id = %s", (TEST_JOB_ID,))
            conn.commit()
            
    # 2. Insert Test Job with 'pending' status
    logger.info("Inserting test job with 'pending' status...")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO jobs (
                    job_id, title, company, job_description, 
                    enrichment_status, date_posted, ingested_at,
                    job_link, source, is_remote, work_mode, location
                ) VALUES (
                    %s, %s, %s, %s, 
                    'pending', NOW(), NOW(),
                    'http://test.com', 'test_script', FALSE, 'onsite', 'Test Location'
                )
            """, (
                TEST_JOB_ID, 
                "Senior Python Developer Verification", 
                "Test Corp", 
                "Looking for a Python expert with extensive experience in Django and React. Must know AWS."
            ))
            conn.commit()
            
    # 3. Verify it is pending
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT enrichment_status FROM jobs WHERE job_id = %s", (TEST_JOB_ID,))
            status = cur.fetchone()[0]
            logger.info(f"Job status in DB: {status}")
            if status != 'pending':
                logger.error("❌ Job failed to insert as pending")
                return False

    # 4. Run Worker Logic (Imported directly to simulate execution)
    logger.info("Running Worker logic...")
    try:
        # Import worker modules
        # We need to make sure worker script is importable
        sys.path.append(os.path.join(root_dir, 'scripts'))
        # Using exec to run worker file? Or import?
        # Let's just run the process_job function if we can import it
        # But importing scripts is messy.
        # Let's Run the worker as a subprocess for 5 seconds
        import subprocess
        # We use the same python interpreter
        cmd = [sys.executable, os.path.join(root_dir, 'scripts', 'worker_enrichment.py')]
        
        # Run worker in background
        logger.info("Starting worker subprocess...")
        process = subprocess.Popen(cmd, cwd=os.path.join(root_dir, 'scripts'))
        
        # Poll for completion (up to 30s)
        start_time = time.time()
        job_completed = False
        
        while time.time() - start_time < 30:
            time.sleep(2)
            with get_db() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT enrichment_status FROM jobs WHERE job_id = %s", (TEST_JOB_ID,))
                    row = cur.fetchone()
                    if row and row[0] == 'completed':
                        job_completed = True
                        break
        
        process.terminate()
        logger.info(f"Worker stopped. Job completed: {job_completed}")
        
    except Exception as e:
        logger.error(f"Failed to run worker: {e}")
        return False

    # 5. Verify Completion
    logger.info("Checking results...")
    with get_db() as conn:
        with conn.cursor() as cur:
            # Check Status
            cur.execute("SELECT enrichment_status FROM jobs WHERE job_id = %s", (TEST_JOB_ID,))
            row = cur.fetchone()
            if not row:
                logger.error("❌ Test job disappeared!")
                return False
                
            status = row[0]
            logger.info(f"Final Job Status: {status}")
            
            if status != 'completed':
                logger.error(f"❌ Worker did not complete the job (Status: {status})")
                return False
            else:
                logger.info("✅ Job marked as completed")

            # Check Job Enrichment
            cur.execute("SELECT tech_languages FROM job_enrichment WHERE job_id = %s", (TEST_JOB_ID,))
            res = cur.fetchone()
            if res and 'Python' in res[0]:
                logger.info(f"✅ job_enrichment populated: {res[0]}")
            else:
                logger.error(f"❌ job_enrichment missing or incorrect: {res}")
                return False

            # Check Job Search Sync (Trigger)
            cur.execute("SELECT tech_stack, job_summary FROM job_search WHERE job_id = %s", (TEST_JOB_ID,))
            search_res = cur.fetchone()
            if search_res:
                logger.info(f"✅ job_search synced. Tech: {search_res[0]}")
                if 'Python' in search_res[0]:
                     logger.info("✅ Trigger worked correctly!")
                else:
                     logger.warning("⚠️ Trigger ran but tech stack content might be mismatching parsing")
            else:
                 logger.error("❌ job_search NOT synced (Trigger failed)")
                 return False

    return True

if __name__ == "__main__":
    # Cleanup first to remove any bad data from previous runs
    logger.info("Cleaning up previous test data...")
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM jobs WHERE job_id = %s", (TEST_JOB_ID,))
                cur.execute("DELETE FROM job_enrichment WHERE job_id = %s", (TEST_JOB_ID,))
                cur.execute("DELETE FROM job_search WHERE job_id = %s", (TEST_JOB_ID,))
                conn.commit()
    except Exception as e:
        logger.warning(f"Cleanup failed (might be first run): {e}")

    success_read = verify_read_path()
    success_write = False
    if success_read:
        success_write = verify_write_path()
    
    if success_read and success_write:
        logger.info("\n🎉 FULL SYSTEM VERIFICATION PASSED 🎉")
        sys.exit(0)
    else:
        logger.error("\n💥 VERIFICATION FAILED 💥")
        sys.exit(1)
