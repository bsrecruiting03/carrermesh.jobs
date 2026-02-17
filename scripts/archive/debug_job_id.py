
import psycopg2
import os
import sys

# Connect to DB
try:
    conn = psycopg2.connect(
        dbname="job_board",
        user="postgres",
        password="password",
        host="job_board_db", # Use container name if running in docker network
        port="5432"
    )
except:
    # Fallback for local run
    try:
        conn = psycopg2.connect(
            dbname="job_board",
            user="postgres",
            password="password",
            host="localhost",
            port="5433"
        )
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

def debug_job_id():
    cur = conn.cursor()
    
    # Target specific job that failed
    target_pattern = '%JR108971%'
    
    print(f"🔍 Searching for job matching: {target_pattern}")
    
    cur.execute("SELECT job_id FROM jobs WHERE job_id LIKE %s LIMIT 1", (target_pattern,))
    row = cur.fetchone()
    
    if not row:
        print("❌ Job NOT FOUND in DB.")
        return

    job_id = row[0]
    print(f"✅ Found Job ID: {repr(job_id)}")
    print(f"   Length: {len(job_id)}")
    print(f"   Bytes: {job_id.encode('utf-8')}")
    
    # Check for whitespace
    if job_id != job_id.strip():
        print("⚠️ WARNING: Job ID has leading/trailing whitespace!")
    
    # Try exact lookup
    print(f"\n🔄 Testing exact lookup with param: {repr(job_id)}")
    cur.execute("SELECT 1 FROM jobs WHERE job_id = %s", (job_id,))
    if cur.fetchone():
        print("✅ Exact lookup SUCCESS.")
    else:
        print("❌ Exact lookup FAILED.")

    conn.close()

if __name__ == "__main__":
    debug_job_id()
