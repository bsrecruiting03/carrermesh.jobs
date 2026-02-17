import json
import os
import sys
import logging

# Add root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from us_ats_jobs.db import database

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(MESSAGE)s')
logger = logging.getLogger("IngestFortune")

def ingest():
    file_path = "fortune500_restructured.json"
    if not os.path.exists(file_path):
        logger.error(f"❌ File not found: {file_path}")
        return

    logger.info(f"📂 Reading {file_path}...")
    with open(file_path, "r") as f:
        data = json.load(f)

    companies = data.get("companies", [])
    total_added = 0
    total_skipped = 0

    if hasattr(database, "init_pool"):
        database.init_pool()

    for company in companies:
        name = company.get("name")
        urls = company.get("urls", {})
        careers = company.get("careers", {})

        website_url = urls.get("company_website")
        career_page = urls.get("careers_page")
        platform = careers.get("platform", "Custom")

        # Map 'Custom' to 'generic' provider which we will implement with Schema.org scraper
        provider = "generic" if platform == "Custom" else platform.lower()
        
        # For Generic/Custom, the ATS URL is the Career Page URL to scrape
        target_ats_url = career_page

        logger.info(f"🚀 Processing {name} ({provider})")

        try:
            # We use 'domain' column to store the main website URL as agreed
            added = database.add_company(
                name=name, 
                ats_url=target_ats_url, 
                ats_provider=provider, 
                career_page_url=career_page, 
                domain=website_url 
            )
            
            if added:
                total_added += 1
                logger.info(f"✅ Added {name}")
            else:
                total_skipped += 1
                logger.info(f"⏭️  Skipped {name} (Duplicate)")
                
        except Exception as e:
            logger.error(f"❌ Error adding {name}: {e}")

    logger.info("-" * 30)
    logger.info(f"🎉 Ingestion Complete!")
    logger.info(f"✅ Added: {total_added}")
    logger.info(f"⏭️ Skipped: {total_skipped}")

if __name__ == "__main__":
    ingest()
