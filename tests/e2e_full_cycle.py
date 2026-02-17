import sys
import os
import logging
import time
import uuid

# Add root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from us_ats_jobs.db import database
from us_ats_jobs import worker_enrichment

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("E2E_Test")

def run_e2e_test():
    job_id = f"test-job-{uuid.uuid4().hex[:8]}"
    company = "Test Corp E2E"
    title = "Senior Python Backend Engineer"
    description = """
    We are looking for a Senior Backend Engineer to join our team.
    
    Requirements:
    - 5+ years of experience with Python and Django.
    - Strong knowledge of AWS (EC2, S3, Lambda).
    - Experience with PostgreSQL and Redis.
    - Ability to design REST APIs.
    
    Benefits:
    - Competitive salary: $150,000 - $200,000 per year.
    - Remote work options.
    - Visa sponsorship available for the right candidate.
    """
    location = "New York, NY"
    
    logger.info(f"🧪 Starting E2E Test for Job ID: {job_id}")

    # --- Step 1: Ingest Job ---
    logger.info("--- Step 1: Ingesting Job ---")
    mock_job = {
        "job_id": job_id,
        "title": title,
        "company": company,
        "location": location,
        "job_description": description,
        "job_link": "https://example.com/job/123",
        "source": "manual_test",
        "date_posted": "2025-01-01"
    }
    
    try:
        database.insert_jobs([mock_job])
        logger.info("✅ Job inserted into 'jobs' table.")
    except Exception as e:
        logger.error(f"❌ Ingestion Failed: {e}")
        return

    # Verify Ingestion
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT title, location, salary_min FROM jobs WHERE job_id = %s", (job_id,))
            row = cur.fetchone()
            if row:
                logger.info(f"   -> Verifying Ingestion: Found Title='{row[0]}'")
                # Note: salary_min might depend on basic regex in insert_jobs, verifying if it worked:
                if row[2]:
                     logger.info(f"   -> Basic Inference working: Salary Min detected as {row[2]}")
                else:
                     logger.warning("   -> Basic Inference validation: Salary Min NOT detected in raw layer (might be normal if strictly enrichment worker task).")
            else:
                logger.error("❌ Job NOT found in DB after insertion!")
                return

    # --- Step 2: Trigger Enrichment ---
    logger.info("--- Step 2: Running Enrichment Worker ---")
    
    # We call process_batch directly. It matches any unenriched job. 
    # Since we just inserted ours, it should pick it up (unless queue is huge).
    
    # Loop max 3 times to try and catch our job
    found_and_processed = False
    for i in range(3):
        count = worker_enrichment.process_batch()
        if count > 0:
            # Check if OUR job was processed
            with database.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM job_enrichment WHERE job_id = %s", (job_id,))
                    if cur.fetchone():
                        found_and_processed = True
                        logger.info("✅ Our test job was processed!")
                        break
        if not found_and_processed:
            logger.info("   ... Worker processed other jobs or none. Retrying batch...")
            time.sleep(1)

    if not found_and_processed:
         logger.error("❌ Worker ran but did not enrich our specific job (maybe queue is backed up?).")
         # Proceed to verify anyway, maybe it missed the check
    
    # --- Step 3: Verify Enrichment Data ---
    logger.info("--- Step 3: verifying Enrichment Artifacts ---")
    
    with database.get_connection() as conn:
        with conn.cursor(cursor_factory=database.psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM job_enrichment WHERE job_id = %s", (job_id,))
            enriched = cur.fetchone()
            
            if not enriched:
                logger.error("❌ No enrichment record found!")
                return

            # Verification Logic
            logger.info(f"   -> Tier: {enriched.get('enrichment_tier')}")
            logger.info(f"   -> Tech Stack: {enriched.get('tech_languages')} | {enriched.get('tech_frameworks')} | {enriched.get('tech_cloud')}")
            
            tech_text = (enriched.get('tech_languages') or "") + (enriched.get('tech_frameworks') or "") + (enriched.get('tech_cloud') or "")
            
            missed = []
            if "Python" not in tech_text: missed.append("Python")
            if "Django" not in tech_text: missed.append("Django")
            if "AWS" not in tech_text: missed.append("AWS")
            
            if missed:
                 logger.error(f"❌ Failed to extract skills: {missed}")
            else:
                 logger.info("✅ Skills Extraction (Layers 1 & 2): SUCCESS")

            # LLM Verification
            if enriched.get('enrichment_tier') == 'premium':
                logger.info("✅ LLM Layer Triggered (Premium Tier)")
                logger.info(f"   -> Seniority: {enriched.get('seniority_tier')}")
                logger.info(f"   -> Summary: {enriched.get('job_summary')}")
            else:
                logger.warning("⚠️ LLM Layer did NOT trigger (Tier is basic). Check logs above for LLM errors or skipping.")

    logger.info("🏁 E2E Test Complete.")

if __name__ == "__main__":
    run_e2e_test()
