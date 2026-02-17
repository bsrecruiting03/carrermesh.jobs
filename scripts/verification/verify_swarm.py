
import sys
import os
import psycopg2
import random
import time
from datetime import date

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))
# Add us_ats_jobs to path so 'import utils' works inside source files
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../us_ats_jobs")))

from api.config import settings
from us_ats_jobs import config
from us_ats_jobs.db import database
from us_ats_jobs.sources.greenhouse import fetch_greenhouse_jobs
from us_ats_jobs.sources.lever import fetch_lever_jobs
from us_ats_jobs.sources.ashby import fetch_ashby_jobs
from us_ats_jobs.sources.workable import fetch_workable_jobs
from us_ats_jobs.normalizer import normalize_greenhouse, normalize_lever, normalize_ashby, normalize_workable

def verify_swarm():
    conn = psycopg2.connect(settings.database_url)
    conn.autocommit = True
    cursor = conn.cursor()
    
    # 1. Select Targets
    # Picking 5 from each (to be faster than 20-50, but substantial) 
    # User asked for "20-50 companies", so let's do 5 x 4 = 20 companies.
    targets = []
    
    # Greenhouse
    gh_sample = random.sample(config.GREENHOUSE_COMPANIES, k=min(5, len(config.GREENHOUSE_COMPANIES)))
    for c in gh_sample: targets.append((c, "greenhouse"))
    
    # Lever
    lv_sample = random.sample(config.LEVER_COMPANIES, k=min(5, len(config.LEVER_COMPANIES)))
    for c in lv_sample: targets.append((c, "lever"))
    
    # Ashby
    as_sample = random.sample(config.ASHBY_COMPANIES, k=min(5, len(config.ASHBY_COMPANIES)))
    for c in as_sample: targets.append((c, "ashby"))
    
    # Workable
    wk_sample = random.sample(config.WORKABLE_COMPANIES, k=min(5, len(config.WORKABLE_COMPANIES)))
    for c in wk_sample: targets.append((c, "workable"))

    print(f"--- SWARM VERIFICATION: {len(targets)} Companies ---")
    
    results = {"pass": 0, "fail": 0, "empty": 0}
    failed_details = []

    for company, provider in targets:
        print(f"\n[Testing] {company} ({provider})")
        
        try:
            # A. Purge
            cursor.execute("DELETE FROM jobs WHERE company ILIKE %s", (company,))
            
            # B. Fetch
            jobs = []
            if provider == "greenhouse": jobs = fetch_greenhouse_jobs(company)
            elif provider == "lever": jobs = fetch_lever_jobs(company)
            elif provider == "ashby": jobs = fetch_ashby_jobs(company)
            elif provider == "workable": jobs = fetch_workable_jobs(company)
            
            if not jobs:
                print(f"   ⚠️ Fetched 0 jobs (Robots/Empty?). Skipping.")
                results["empty"] += 1
                continue
                
            print(f"   Fetched {len(jobs)} jobs.")

            # C. Normalize
            norm_jobs = []
            for j in jobs:
                if provider == "greenhouse": n = normalize_greenhouse(j, company)
                elif provider == "lever": n = normalize_lever(j, company)
                elif provider == "ashby": n = normalize_ashby(j, company)
                elif provider == "workable": n = normalize_workable(j, company)
                norm_jobs.append(n)
            
            # D. Insert
            count = database.insert_jobs(norm_jobs)
            print(f"   ✅ Inserted {count} jobs.")
            
            # E. Verify
            cursor.execute("SELECT COUNT(*) FROM jobs WHERE company ILIKE %s", (company,))
            db_count = cursor.fetchone()[0]
            
            if db_count > 0:
                results["pass"] += 1
            else:
                 print(f"   ❌ DB Count is 0 after insert!")
                 results["fail"] += 1
                 failed_details.append(f"{company}: Inserted 0")

        except Exception as e:
            print(f"   ❌ CRASH: {e}")
            results["fail"] += 1
            failed_details.append(f"{company}: {str(e)}")

    print("\n--- RESULTS ---")
    print(f"PASS : {results['pass']}")
    print(f"FAIL : {results['fail']}")
    print(f"EMPTY: {results['empty']}")
    if failed_details:
        print("Failures:")
        for f in failed_details: print(f"- {f}")

    conn.close()

if __name__ == "__main__":
    verify_swarm()
