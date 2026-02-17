import sys
import os
import logging

# Add root to python path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from us_ats_jobs.db import database
from us_ats_jobs.queue.redis_manager import queue_manager

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Scheduler")

def schedule_jobs():
    logger.info("📅 Starting Scheduler...")

    # 1. Fetch Active Companies from DB
    try:
        companies = database.get_active_companies()
        logger.info(f"Checking {len(companies)} active companies...")
    except Exception as e:
        logger.error(f"Failed to fetch companies from DB: {e}")
        return

    # 2. Filter Logic (Optional - e.g., Scrape Frequency)
    # For now, we push ALL that are active and not circuit-broken (handled by get_active_companies)
    
    # 3. Push to Redis
    count = 0
    for company in companies:
        payload = {
            "id": company["id"],
            "name": company["name"],
            "ats_provider": company["ats_provider"],
            "ats_url": company.get("ats_url") # Include generic fields
        }
        
        if queue_manager.push_company_task(payload):
            count += 1
        
        if count % 1000 == 0:
            logger.info(f"Queued {count} companies...")

    logger.info(f"✅ Successfully queued {count} companies for scraping.")
    
    # Status Check
    status = queue_manager.get_queue_status()
    logger.info(f"Queue Status: {status}")

if __name__ == "__main__":
    schedule_jobs()
