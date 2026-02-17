
import sys
import os
import logging

# Add root
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "us_ats_jobs"))

from us_ats_jobs.worker_scraper import process_company

# Mock Task
task = {
    "type": "endpoint_ingest",
    "ats_provider": "custom_amazon",
    "ats_slug": "amazon",
    "endpoint_url": "https://www.amazon.jobs/en/search.json",
    "correlation_id": "test-amazon-1"
}

logging.basicConfig(level=logging.INFO)

print("🚀 Starting Amazon Ingestion Verification...")
success = process_company(task)

if success:
    print("✅ Amazon ingestion successful!")
else:
    print("❌ Amazon ingestion failed.")
