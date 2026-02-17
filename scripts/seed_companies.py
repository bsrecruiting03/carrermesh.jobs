import json
import os
import sys
import logging

# Add root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from us_ats_jobs.db import database

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Seeder")

PROVIDERS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{}/jobs",
    "lever": "https://api.lever.co/v3/postings/{}",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{}",
    "workable": "https://apply.workable.com/api/v1/widget/accounts/{}"
}

def seed():
    file_path = "companies.json"
    if not os.path.exists(file_path):
        logger.error(f"❌ File not found: {file_path}")
        return

    logger.info(f"📂 Reading {file_path}...")
    with open(file_path, "r") as f:
        data = json.load(f)

    total_added = 0
    total_skipped = 0

    # Initialize Pool
    if hasattr(database, "init_pool"):
        database.init_pool()

    for provider, slugs in data.items():
        template = PROVIDERS.get(provider)
        if not template:
            logger.warning(f"⚠️ Unknown provider pattern: {provider}. Using generic.")
            template = "https://example.com/{}"
            
        logger.info(f"🚀 Seeding {len(slugs)} companies for {provider}...")
        
        for slug in slugs:
            ats_url = template.format(slug)
            # Add to DB
            try:
                # add_company(name, ats_url, ats_provider, ...)
                # Assuming name=slug for the worker to function correctly
                added = database.add_company(slug, ats_url, provider)
                if added:
                    total_added += 1
                else:
                    total_skipped += 1 # Likely duplicate
            except Exception as e:
                logger.error(f"❌ Error adding {slug}: {e}")

    logger.info(f"🎉 Seeding Complete!")
    logger.info(f"✅ Added: {total_added}")
    logger.info(f"⏭️ Skipped (Duplicates): {total_skipped}")

if __name__ == "__main__":
    seed()
