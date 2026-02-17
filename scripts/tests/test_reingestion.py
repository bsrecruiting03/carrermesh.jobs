
import sys
import os
import psycopg2
from datetime import date

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))

from api.config import settings
from us_ats_jobs.sources.greenhouse import fetch_greenhouse_jobs
from us_ats_jobs.normalizer import normalize_greenhouse
from us_ats_jobs.db import database

def test_reingestion():
    conn = psycopg2.connect(settings.database_url)
    conn.autocommit = True
    cursor = conn.cursor()
    
    company_name = "stripe"
    print(f"--- Re-Ingestion Test for {company_name} ---")

    # 1. Count existing
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE company ILIKE %s", (company_name,))
    initial_count = cursor.fetchone()[0]
    print(f"1. Initial Stripe Jobs in DB: {initial_count}")
    
    # 2. Delete
    print("2. Deleting Stripe jobs...")
    cursor.execute("DELETE FROM jobs WHERE company ILIKE %s", (company_name,))
    cursor.execute("DELETE FROM raw_jobs WHERE source = 'greenhouse'") # cleanup raw too just in case of constraints, though usually job_id key
    # Actually normalizer uses job_id, so deleting from jobs is enough to allow re-insertion.
    print("   Deleted.")
    
    # 3. Fetch & Insert Manually (simulating main loop)
    print("3. Fetching live from Greenhouse...")
    try:
        jobs = fetch_greenhouse_jobs(company_name)
        print(f"   Fetched {len(jobs)} jobs from API.")
        
        normalized_jobs = []
        for job in jobs:
            normalized_jobs.append(normalize_greenhouse(job, company_name))
            
        print(f"   Normalizing {len(normalized_jobs)} jobs...")
        
        # Insert
        print("   Inserting into DB...")
        count = database.insert_jobs(normalized_jobs)
        print(f"   DB Insert Return Count: {count}")

    except Exception as e:
        print(f"   ❌ Error during fetch/insert: {e}")
        conn.close()
        return

    # 4. Verify
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE company ILIKE %s", (company_name,))
    final_count = cursor.fetchone()[0]
    print(f"4. Final Stripe Jobs in DB: {final_count}")
    
    cursor.execute("SELECT COUNT(*) FROM jobs WHERE company ILIKE %s AND ingested_at >= %s", (company_name, date.today().isoformat()))
    today_count = cursor.fetchone()[0]
    print(f"5. Jobs marked as 'Ingested Today': {today_count}")

    conn.close()

if __name__ == "__main__":
    test_reingestion()
