import sys
import os
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Ensure imports work
sys.path.append(os.path.join(os.path.dirname(__file__), "us_ats_jobs"))

import db.database as database
from sources.workday import fetch_workday_jobs
from normalizer import normalize_workday

def process_company(company):
    slug = company['name'] # In our import, name IS the slug
    try:
        raw_jobs = fetch_workday_jobs(slug)
        if not raw_jobs:
            return []
            
        normalized_jobs = []
        for job in raw_jobs:
            # We pass slug as company_name too, normalizer handles it
            norm = normalize_workday(job, slug, slug)
            
            # Save raw JSON for debugging
            database.save_raw_job(norm['job_id'], 'workday', job)
            normalized_jobs.append(norm)
            
        # Optional: Mark success in DB (main.py does this)
        # database.record_company_success(company['id'])
        
        return normalized_jobs
    except Exception as e:
        print(f"❌ Failed processing {slug}: {e}")
        return []

def main():
    print("🚀 Starting Workday Ingestion...")
    database.create_tables()
    
    # 1. Get Companies
    all_companies = database.get_active_companies()
    workday_companies = [c for c in all_companies if c.get('ats_provider') == 'workday']
    
    print(f"📋 Found {len(workday_companies)} Workday companies in database.")
    
    if not workday_companies:
        print("⚠️ No companies found. Did you run 'import_from_json.py'?")
        return

    # 2. Crawl in Parallel
    all_jobs_data = []
    start_time = time.time()
    
    # Worker count - high for I/O bound tasks
    WORKERS = 30
    
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(process_company, c): c for c in workday_companies}
        
        completed = 0
        total = len(workday_companies)
        
        for future in as_completed(futures):
            completed += 1
            if completed % 50 == 0:
                print(f"   Progress: {completed}/{total} companies checked...")
                
            jobs = future.result()
            all_jobs_data.extend(jobs)

    duration = time.time() - start_time
    print(f"\n✅ Crawl Finished in {duration:.1f}s")
    print(f"📊 Total Raw Jobs Found: {len(all_jobs_data)}")
    
    # 3. Save to Database
    if all_jobs_data:
        print("💾 Saving to Database...")
        df = pd.DataFrame(all_jobs_data)
        
        # Deduplicate
        initial_count = len(df)
        df.drop_duplicates(subset=['job_id'], inplace=True)
        final_count = len(df)
        if initial_count != final_count:
            print(f"   Removed {initial_count - final_count} duplicate job IDs")
            
        # Insert
        try:
            inserted = database.insert_jobs(df.to_dict(orient='records'))
            print(f"✅ Successfully inserted {inserted} jobs into 'jobs' table.")
        except Exception as e:
            print(f"❌ Database Insertion Failed: {e}")
            # Dump to JSON just in case
            df.to_json("workday_jobs_backup.json", orient="records")
            print("   Dumped to workday_jobs_backup.json")
    else:
        print("⚠️ No jobs found to save.")

if __name__ == "__main__":
    main()
