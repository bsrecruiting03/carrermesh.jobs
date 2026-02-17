import sys
import os
import psycopg2
from psycopg2 import extras

# Ensure package path is correct
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "us_ats_jobs"))

# Get DB config directly from env or use default
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/job_board")

def check_stats():
    print(f"📊 Connecting to: {DB_URL}")
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        
        # 1. Jobs by Source
        print("\n--- 📈 Jobs by Source ---")
        cur.execute("""
            SELECT source, count(*) as count 
            FROM jobs 
            GROUP BY source 
            ORDER BY count DESC
        """)
        for row in cur.fetchall():
            print(f"  {row['source']}: {row['count']}")
            
        # 2. Workday specific stats
        print("\n--- 🏢 Workday Details ---")
        cur.execute("""
            SELECT count(*) FROM jobs WHERE source = 'workday'
        """)
        wd_jobs = cur.fetchone()['count']
        
        cur.execute("""
            SELECT count(DISTINCT company) FROM jobs WHERE source = 'workday'
        """)
        wd_companies = cur.fetchone()['count']
        
        if wd_companies > 0:
            print(f"  Total Workday Jobs: {wd_jobs}")
            print(f"  Companies with Jobs: {wd_companies}")
            print(f"  Avg Jobs/Company: {wd_jobs / wd_companies:.1f}")
        else:
            print("  No Workday jobs found.")

        # 3. Recent Activity (Postgres Timestamps)
        print("\n--- 🕒 Recent Activity (Last 24h) ---")
        cur.execute("""
            SELECT source, count(*) 
            FROM jobs 
            WHERE ingested_at >= CURRENT_DATE 
            GROUP BY source
        """)
        rows = cur.fetchall()
        if rows:
            for row in rows:
                print(f"  {row['source']}: {row['count']}")
        else:
            print("  No jobs ingested in the last 24h.")
            
        # 4. Intelligence Status
        print("\n--- 🧠 Intelligence Coverage ---")
        cur.execute("SELECT count(*) FROM jobs WHERE is_remote IS NOT NULL")
        processed = cur.fetchone()['count']
        print(f"  Processed for Remote: {processed}")
        
        cur.execute("SELECT count(*) FROM job_enrichment")
        enriched = cur.fetchone()['count']
        print(f"  Enriched (Tech Stack): {enriched}")

        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_stats()
