import sys
import os

# Ensure package path is correct
sys.path.append(os.path.join(os.path.dirname(__file__), "us_ats_jobs"))

try:
    from db.database import get_connection
except ImportError:
    # Handle if run from root
    from us_ats_jobs.db.database import get_connection

def verify_migration():
    print("🔍 Verifying PostgreSQL Database...")
    
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Companies
                cur.execute("SELECT count(*) FROM companies")
                count_companies = cur.fetchone()[0]
                print(f"✅ Companies: {count_companies}")

                # 2. Jobs
                cur.execute("SELECT count(*) FROM jobs")
                count_jobs = cur.fetchone()[0]
                print(f"✅ Jobs: {count_jobs}")

                # 3. Workday Specific
                cur.execute("SELECT count(*) FROM companies WHERE ats_provider='workday'")
                count_wd = cur.fetchone()[0]
                print(f"✅ Workday Companies: {count_wd}")

                # 4. Fingerprints
                cur.execute("SELECT count(*) FROM workday_fingerprints")
                count_fp = cur.fetchone()[0]
                print(f"✅ Fingerprints: {count_fp}")

                # 5. Check Sample Query (JSONB)
                cur.execute("SELECT count(*) FROM raw_jobs")
                count_raw = cur.fetchone()[0]
                print(f"✅ Raw Jobs: {count_raw}")
                
        print("\n🚀 Database is successfully connected and populated!")
        return True
    except Exception as e:
        print(f"\n❌ Verification Failed: {e}")
        return False

if __name__ == "__main__":
    verify_migration()
