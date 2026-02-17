import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, '.env'))

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

try:
    print("\n--- GEMINI 2.0 FLASH VERIFICATION ---")
    
    # Check count in last 5 minutes
    cur.execute("SELECT COUNT(*) FROM job_enrichment WHERE last_enriched_at > NOW() - INTERVAL '5 minutes'")
    count = cur.fetchone()[0]
    print(f"Jobs enriched in last 5 mins: {count}")
    
    if count > 0:
        # Check details of last 3
        cur.execute("""
            SELECT j.title, j.company, je.seniority, je.remote_policy, je.last_enriched_at
            FROM jobs j 
            JOIN job_enrichment je ON j.job_id = je.job_id 
            ORDER BY je.last_enriched_at DESC 
            LIMIT 3
        """)
        samples = cur.fetchall()
        print("\nLatest Samples:")
        for s in samples:
            print(f" - Title: {s[0]}")
            print(f"   Company: {s[1]}")
            print(f"   Seniority: {s[2]} | Remote: {s[3]}")
            print(f"   Time: {s[4]}")
            print("-" * 30)
    else:
        print("\n⚠️ No jobs enriched in the last 5 minutes.")
        print("Checking for recent failures...")
        cur.execute("SELECT job_id, error_log, updated_at FROM jobs WHERE enrichment_status = 'failed' ORDER BY updated_at DESC LIMIT 3")
        failures = cur.fetchall()
        for f in failures:
            print(f" - Job {f[0]} failed at {f[2]}")
            print(f"   Error: {f[1]}")
            
except Exception as e:
    print(f"Verification Error: {e}")
finally:
    conn.close()
