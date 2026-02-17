import os
import sys
import psycopg2
from datetime import datetime, timedelta

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

def check_ingestion_status():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        # 1. How many jobs ingested in last hour?
        cur.execute("""
            SELECT COUNT(*) 
            FROM raw_jobs 
            WHERE fetched_at > NOW() - INTERVAL '1 hour'
        """)
        last_hour = cur.fetchone()[0]
        
        # 2. How many endpoints are "Due" (last_checked + interval < now)?
        # Assuming 24h interval for now, or check scraping_interval logic.
        # Let's assume standard is 24h.
        cur.execute("""
            SELECT COUNT(*) 
            FROM career_endpoints 
            WHERE active = TRUE 
            AND (last_ingested_at IS NULL OR last_ingested_at < NOW() - INTERVAL '6 hours')
        """)
        due_endpoints = cur.fetchone()[0]
        
        # 3. Total Active
        cur.execute("SELECT COUNT(*) FROM career_endpoints WHERE active = TRUE")
        total_active = cur.fetchone()[0]
        
        print(f"\n🚀 Ingestion Status")
        print(f"-------------------")
        print(f"⚡ Velocity: {last_hour:,} jobs/hour")
        print(f"   ( Projected: {last_hour * 24:,} jobs/day )")
        print(f"")
        print(f"📋 Task Pool:")
        print(f"   - Total Endpoints: {total_active:,}")
        print(f"   - Due for scraping: {due_endpoints:,}")
        
        needed_per_hour = 10000 / 12 # roughly
        print(f"")
        if last_hour > 400:
            print("✅ ON TRACK: Current speed is sufficient for >10k today.")
        else:
            print("⚠️  BOOST NEEDED: Need to accelerate.")
            
    finally:
        conn.close()

if __name__ == "__main__":
    check_ingestion_status()
