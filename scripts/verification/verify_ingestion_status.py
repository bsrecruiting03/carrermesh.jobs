
import sys
import os
import psycopg2
from datetime import datetime, date

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))

from api.config import settings

def verify_ingestion():
    conn = None
    try:
        conn = psycopg2.connect(settings.database_url)
        cur = conn.cursor()
        
        print(f"Time Now: {datetime.now()}")
        
        # 1b. Check Total Jobs
        cur.execute("SELECT COUNT(*) FROM jobs")
        total_jobs = cur.fetchone()[0]
        print(f"Total Jobs in DB: {total_jobs}")

        # 1. Check Jobs Ingested Today
        today = date.today().isoformat()
        cur.execute("SELECT COUNT(*) FROM jobs WHERE ingested_at >= %s", (today,))
        count_today = cur.fetchone()[0]
        print(f"Jobs Ingested Today ({today}): {count_today}")
        
        # 2. Check Most Recent Job
        cur.execute("SELECT title, company, ingested_at FROM jobs ORDER BY ingested_at DESC LIMIT 1")
        row = cur.fetchone()
        if row:
            print(f"Most Recent Job: '{row[0]}' at {row[1]} from {row[2]}")
        else:
            print("No jobs found.")
            
        # 3. Check Company Successes (Last Hour)
        cur.execute("""
            SELECT COUNT(*) FROM companies 
            WHERE last_success_at >= NOW() - INTERVAL '1 hour'
        """)
        companies_updated = cur.fetchone()[0]
        print(f"Companies successfully scraped in last 1 hour: {companies_updated}")

        # 4. Check Raw Jobs count
        cur.execute("SELECT COUNT(*) FROM raw_jobs")
        raw_count = cur.fetchone()[0]
        print(f"Total Raw Jobs: {raw_count}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    verify_ingestion()
