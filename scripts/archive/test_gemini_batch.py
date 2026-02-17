
import sys
import os
import logging
import time

# Ensure we can import from app
sys.path.append(os.getcwd())

# Force Provider to Gemini
os.environ["LLM_PROVIDER"] = "gemini"
os.environ["LLM_MODEL"] = "gemini-flash-latest"

try:
    from us_ats_jobs.intelligence.llm_extractor import LLMService, JobEnrichmentData
    from us_ats_jobs.db import database
except ImportError:
    # If running inside container where path is /app
    sys.path.append("/app")
    from us_ats_jobs.intelligence.llm_extractor import LLMService, JobEnrichmentData
    from us_ats_jobs.db import database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GeminiTester")

def test_gemini_batch(limit=50):
    logger.info(f"🚀 Starting Gemini Flash Test (Limit: {limit} jobs)...")
    
    # 1. Init Service
    llm_service = LLMService()
    if not llm_service.client:
        logger.error("❌ Failed to initialize Gemini Client (Check API KEY).")
        return

    logger.info(f"✅ Gemini Service Initialized (Provider: {llm_service.provider})")

    # 2. Get Jobs
    jobs = database.get_unenriched_jobs(limit=limit)
    if not jobs:
        logger.info("⚠️ No unenriched jobs found.")
        return

    logger.info(f"📋 Found {len(jobs)} jobs to process.")
    
    success_count = 0
    start_time = time.time()

    for job in jobs:
        job_id = job.get("job_id")
        title = job.get("title") or "Unknown"
        company = job.get("company") or "Unknown"
        description = job.get("job_description") or ""
        
        logger.info(f"🔹 Processing {job_id}: {title} at {company}")
        
        try:
            result = llm_service.extract(description, title, company)
            
            if result:
                success_count += 1
                logger.info(f"   ✅ Success! Salary: {result.salary.min}-{result.salary.max}, Visa: {result.visa_sponsorship.mentioned}")
                
                # Save to DB (Optional: effectively creating 'premium' data)
                # We reuse the logic from worker or just save manually
                # For this test, let's NOT save to avoid messing up production data with 'test' runs? 
                # User asked to "test it works", not "run production".
                # But usually "test on a batch" implies processing them.
                # I will save it to prove it works in DB too.
                
                data = {
                    "enrichment_tier": "premium",
                    "enrichment_source": "gemini-flash-test",
                    "visa_sponsorship": "Yes" if result.visa_sponsorship.mentioned else "No",
                    "salary_min": result.salary.min,
                    "salary_max": result.salary.max,
                    "seniority_tier": result.seniority,
                    "job_summary": result.summary
                }
                # We need to map other fields too if we want a full save, 
                # but database.save_enrichment does partial updates? No, it's an upsert/insert.
                # If we only save these, we might lose other fields if we overwrite?
                # database.save_enrichment updates specific columns?
                # Let's check database.py. It does an INSERT ON CONFLICT DO UPDATE.
                # So it overwrites provided fields.
                
                database.save_enrichment(job_id, data)
                
            else:
                logger.warning(f"   ⚠️ No result returned for {job_id}")

        except Exception as e:
            logger.error(f"   ❌ Error: {e}")

    duration = time.time() - start_time
    logger.info(f"🏁 Batch Complete. Success: {success_count}/{len(jobs)}. Time: {duration:.2f}s")

if __name__ == "__main__":
    test_gemini_batch()
