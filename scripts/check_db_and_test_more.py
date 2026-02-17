import sys
import os
import logging
import psycopg2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from us_ats_jobs.sources.generic import fetch_generic_jobs

logging.basicConfig(level=logging.INFO)

def check_db():
    print("📊 Checking Database...")
    try:
        from us_ats_jobs.db.database import get_connection
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM companies WHERE ats_provider = 'generic'")
                count = cur.fetchone()[0]
                print(f"✅ Found {count} 'generic' companies in DB.")
                
                cur.execute("SELECT name, ats_url FROM companies WHERE ats_provider = 'generic' LIMIT 3")
                print("Examples:", cur.fetchall())
    except Exception as e:
        print(f"❌ DB Check failed: {e}")

def test_others():
    targets = [
        ("Microsoft", "https://careers.microsoft.com/us/en"),
        ("Google", "https://careers.google.com/"), 
    ]
    
    for name, url in targets:
        print(f"\n🧪 Testing {name} ({url})...")
        jobs = fetch_generic_jobs(name, url)
        print(f"Result: {len(jobs)} jobs found.")

if __name__ == "__main__":
    check_db()
    test_others()
