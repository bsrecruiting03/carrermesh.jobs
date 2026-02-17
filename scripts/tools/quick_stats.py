import os
import sys
import psycopg2
from collections import Counter

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

def quick_stats():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        # 1. Total Jobs
        cur.execute("SELECT COUNT(*) FROM jobs")
        total_jobs = cur.fetchone()[0]
        
        # 2. Raw Count
        cur.execute("SELECT COUNT(*) FROM raw_jobs")
        raw_count = cur.fetchone()[0]
        
        # 3. By Provider (from career_endpoints linkage if possible, or source column?)
        # jobs table has 'source' column? Let's check schema. 
        # jobs has 'source', 'job_link', 'company'.
        # We can guess provider from job_link or query companies.
        # Let's just group by 'source' if populated.
        
        cur.execute("SELECT source, COUNT(*) FROM jobs GROUP BY source ORDER BY COUNT(*) DESC LIMIT 10")
        sources = cur.fetchall()
        
        print(f"\n📊 System Job Stats")
        print(f"-------------------")
        print(f"✅ Total Unique Jobs: {total_jobs:,}")
        print(f"📥 Raw Payloads:      {raw_count:,}")
        print(f"")
        print(f"📈 Top Sources:")
        for source, count in sources:
            print(f"   - {source or 'Unknown'}: {count:,}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    quick_stats()
