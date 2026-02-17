
import time
import subprocess
import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SCHEDULER] - %(levelname)s - %(message)s')
logger = logging.getLogger("Scheduler")

# Intervals (in seconds)
SCRAPE_INTERVAL = 6 * 3600  # 6 Hours
SYNC_INTERVAL = 3600        # 1 Hour

def run_scraper():
    logger.info("⏰ Triggering Scheduled Scraping...")
    try:
        # Run the schedule_scraping script as a subprocess
        # This script pushes tasks to Redis
        result = subprocess.run([sys.executable, "scripts/schedule_scraping.py"], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ Scraper triggered successfully.")
            logger.info(result.stdout)
        else:
            logger.error(f"❌ Scraper trigger failed: {result.stderr}")
    except Exception as e:
        logger.error(f"❌ Error running scraper: {e}")

def run_syncer():
    logger.info("⏰ Triggering Search Sync...")
    try:
        # Run the sync_meilisearch script
        result = subprocess.run([sys.executable, "scripts/sync_meilisearch.py"], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ Search sync completed successfully.")
            # Verify success from output or just assume?
            # The script logs "Sync Complete" on success.
            # We can log the last few lines of stdout
            logger.info(result.stdout[-200:]) 
        else:
            logger.error(f"❌ Search sync failed: {result.stderr}")
    except Exception as e:
        logger.error(f"❌ Error running syncer: {e}")

def main():
    logger.info("🚀 Scheduler Service Started")
    logger.info(f"   - Scraping every {SCRAPE_INTERVAL/3600} hours")
    logger.info(f"   - Syncing every {SYNC_INTERVAL/3600} hours")

    # Initial Run?
    # Maybe we want to run immediately on startup?
    # Or maybe wait. Let's run Sync immediately to ensure index is fresh on restart.
    # Scrape might be heavy, so let's skip immediate scrape unless user asks.
    # Actually, automation implies it keeps things running.
    # Let's set initial last_run times to (now - interval) to force immediate run?
    # No, that might overload on a crash-loop.
    # Let's just track time.
    
    # Startup State
    # We skip the first scrape to avoid flooding the queue if the container restarts frequently.
    # We run the first sync immediately to ensure the search index is up-to-date.
    
    last_scrape = time.time() 
    last_sync = 0 
    
    logger.info("⏳ Waiting 60s before loop start...")
    time.sleep(60) 

    while True:
        now = time.time()
        
        # Scrape Check
        if now - last_scrape > SCRAPE_INTERVAL:
            run_scraper()
            last_scrape = time.time()
            
        # Sync Check
        if now - last_sync > SYNC_INTERVAL:
            run_syncer()
            last_sync = time.time()
            
        # Sleep
        time.sleep(60)

if __name__ == "__main__":
    main()
