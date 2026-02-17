import sys
import os
import time
import logging

# Add root project directory to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, 'us_ats_jobs'))

from us_ats_jobs.db import database
from us_ats_jobs.worker_scraper import process_company, logger as worker_logger

def reconfigure_logging():
    """
    Switches the worker logger from JSON (for machines) to Text (for humans).
    """
    # Remove existing handlers (JSON formatters)
    if worker_logger.hasHandlers():
        worker_logger.handlers.clear()
    
    # Add human-readable handler
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('time="%(asctime)s" level=%(levelname)s msg="%(message)s"', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    worker_logger.addHandler(handler)
    worker_logger.setLevel(logging.INFO)

def main():
    reconfigure_logging()
    
    print("📋 Fetching active companies from database...")
    try:
        companies = database.get_active_companies()
    except Exception as e:
        print(f"❌ Database error: {e}")
        return

    # Filter for Workday
    workday_companies = [c for c in companies if c.get('ats_provider') == 'workday']
    
    total = len(workday_companies)
    print(f"✅ Found {total} Workday companies to process.")
    
    if total == 0:
        print("Nothing to do. Exiting.")
        return

    print("\n🚀 Starting ingestion... (Press Ctrl+C to stop)\n")
    
    processed_count = 0
    success_count = 0
    
    try:
        for i, company in enumerate(workday_companies):
            processed_count += 1
            progress = f"[{processed_count}/{total}]"
            
            # Create standard task payload expected by worker
            task = {
                "id": company["id"],
                "name": company["name"],
                "ats_provider": "workday",
                "ats_url": company.get("ats_url"),
                "correlation_id": f"manual-workday-{int(time.time())}",
                "retry_count": 0
            }
            
            print(f"{progress} Processing {company['name']}...")
            
            # process_company returns True if successful (found jobs or no jobs but no error), False if error
            result = process_company(task)
            
            if result:
                success_count += 1
                
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user.")
    
    print(f"\n✨ Summary: Processed {processed_count}/{total} companies. Successful: {success_count}.")

if __name__ == "__main__":
    main()
