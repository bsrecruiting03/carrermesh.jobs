
import sys
import os
import time
import logging

# Add root to python path
sys.path.append("/app") 
sys.path.append(os.getcwd())

from us_ats_jobs.worker_enrichment import process_batch
from us_ats_jobs.db import database

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TestEnrichment")

def test_enrichment():
    print("🚀 Starting Batch Enrichment Test (Limit 50)...")
    
    # 1. Run the worker batch
    processed_count = process_batch()
    
    print(f"\n✅ Processed {processed_count} jobs.")
    
    if processed_count == 0:
        print("⚠️ No unenriched jobs found in DB. Reset some jobs to NULL if you need to re-test.")
        return

    # 2. Verify Data
    print("\n🔍 Verifying Enriched Data (Sample 5):")
    
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            # Fetch recently enriched jobs
            cur.execute("""
                SELECT 
                    j.title, 
                    je.salary_min, je.salary_max, je.salary_currency,
                    je.seniority_tier, 
                    je.visa_sponsorship,
                    je.tech_languages,
                    je.job_summary
                FROM job_enrichment je
                JOIN jobs j ON je.job_id = j.job_id
                ORDER BY je.enriched_at DESC
                LIMIT 5
            """)
            rows = cur.fetchall()
            
            for i, row in enumerate(rows, 1):
                title, s_min, s_max, s_curr, seniority, visa, tech, summary = row
                print(f"\nJob #{i}: {title}")
                print(f"   💰 Salary: {s_min}-{s_max} {s_curr}")
                print(f"   🎓 Seniority: {seniority}")
                print(f"   🛂 Visa: {visa}")
                print(f"   💻 Tech: {tech[:50]}..." if tech else "   💻 Tech: None")
                print(f"   📝 Summary: {summary[:100]}...")

if __name__ == "__main__":
    test_enrichment()
