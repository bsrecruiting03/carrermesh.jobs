import os
import sys
import psycopg2
from datetime import datetime, timedelta

# Add root
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)

def check():
    conn = psycopg2.connect("postgresql://postgres:password@127.0.0.1:5433/job_board")
    cur = conn.cursor()
    
    print(f"Time: {datetime.now()}")
    print("-" * 50)
    
    # 1. Total by Source
    cur.execute("""
        SELECT discovered_from, COUNT(*) 
        FROM career_endpoints 
        GROUP BY discovered_from 
        ORDER BY COUNT(*) DESC
    """)
    rows = cur.fetchall()
    print("📊 Discovery Sources Breakdown:")
    total_new = 0
    for source, count in rows:
        print(f"   - {source}: {count}")
        if source and "workday" in source:
            total_new += count
            
    print("-" * 50)
    print(f"🎯 Total Workday Discovered: {total_new}")
    
    # 2. Sample of Recent Workday Findings
    cur.execute("""
        SELECT ats_slug, ats_provider, created_at 
        FROM career_endpoints
        WHERE discovered_from LIKE '%workday%'
        ORDER BY created_at DESC
        LIMIT 20
    """)
    recent = cur.fetchall()
    print("\n🕵️  Last 20 Detected Workday Tenants:")
    for slug, provider, created in recent:
        print(f"   - {slug} ({provider}) @ {created}")

    # 3. Total Jobs currently in DB
    cur.execute("SELECT COUNT(*) FROM jobs")
    job_count = cur.fetchone()[0]
    print(f"\n📈 Total Jobs Ingested: {job_count}")

    conn.close()

if __name__ == "__main__":
    check()
