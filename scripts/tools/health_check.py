import os
import sys
import psycopg2
import time
from datetime import datetime, timedelta

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

def run_health_check():
    print("🏥 Running System Health Check...")
    
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        # 1. Endpoint Stats
        cur.execute("SELECT COUNT(*) FROM career_endpoints")
        total_endpoints = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM career_endpoints WHERE active = TRUE")
        active_endpoints = cur.fetchone()[0]
        
        # Ingested recently (Last 1 hour)
        cur.execute("""
            SELECT COUNT(*) FROM career_endpoints 
            WHERE last_ingested_at > NOW() - INTERVAL '1 hour'
        """)
        recently_ingested = cur.fetchone()[0]
        
        # Failures (Last 1 hour) -- heuristic: last_ingested updated but consecutive_failures > 0? 
        # Or check last_ingested_at + failures.
        # Actually if it failed, we updated last_ingested_at too (in record_endpoint_result mock? No, only update failure/counts)
        # Wait, my record_endpoint_result only updates last_ingested_at on SUCCESS.
        # So failures don't bump timestamp? 
        # Update: In record_endpoint_result override:
        # Success: Update last_ingested_at.
        # Failure: Update consecutive_failures.
        
        cur.execute("SELECT COUNT(*) FROM career_endpoints WHERE consecutive_failures > 0")
        failing_endpoints = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM career_endpoints WHERE verification_status = 'verified'")
        verified_endpoints = cur.fetchone()[0]

        # 2. Job Stats
        # Jobs ingested in last 1 hour
        cur.execute("""
            SELECT COUNT(*) FROM jobs 
            WHERE ingested_at = CURRENT_DATE 
            -- We don't have ingested_timestamp in jobs, only date. 
            -- But we can check raw_jobs.fetched_at!
        """)
        todays_jobs_approx = cur.fetchone()[0]
        
        cur.execute("""
            SELECT COUNT(*) FROM raw_jobs 
            WHERE fetched_at > NOW() - INTERVAL '1 hour'
        """)
        jobs_last_hour = cur.fetchone()[0]

        print("\n📊 Career Endpoints Status")
        print(f"   - Total: {total_endpoints}")
        print(f"   - Active: {active_endpoints}")
        print(f"   - Verified: {verified_endpoints}")
        print(f"   - Ingested (Last 1h): {recently_ingested}")
        print(f"   - Failing: {failing_endpoints}")
        
        print("\n📉 Ingestion Volume")
        print(f"   - Jobs Fetched (Last 1h): {jobs_last_hour}")
        print(f"   - Jobs (Today): {todays_jobs_approx}")
        
        # 3. Queue / Worker Activity (Inferential)
        if recently_ingested > 0 or jobs_last_hour > 0:
            print("\n✅ System appears ACTIVE.")
            print("   Data is flowing into the database.")
        else:
            print("\n⚠️  System appears IDLE or BLOCKED.")
            print("   No recent ingestion activity found.")

        conn.close()
        
    except Exception as e:
        print(f"❌ Health Check Failed: {e}")

if __name__ == "__main__":
    run_health_check()
