"""
Daily Ingestion Report Generator

Calculates:
1. Jobs ingested in the last 24 hours (total & by ATS)
2. Active companies vs Total companies
3. Companies scraped in last 24h
4. Job failures/Errors (if logged)
"""

import os
import sys
import psycopg2
from datetime import datetime, timedelta
from collections import defaultdict

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# Fallback for direct execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force correct URL to bypass config issues
DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

def generate_report():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    print("\n📊 DAILY INGESTION REPORT")
    print("=" * 40)
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. Job Stats (Last 24h)
    cur.execute("""
        SELECT COUNT(*), COUNT(DISTINCT company)
        FROM jobs 
        WHERE date_posted >= NOW() - INTERVAL '24 hours'
    """)
    new_jobs, active_companies_24h = cur.fetchone()
    
    # 2. Total Stats
    cur.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cur.fetchone()[0]
    
    # Try getting active jobs from job_search, else fallback
    try:
        cur.execute("SELECT COUNT(*) FROM job_search WHERE is_active = TRUE")
        active_jobs = cur.fetchone()[0]
    except psycopg2.Error:
        conn.rollback()
        active_jobs = "N/A (job_search table missing or invalid)"
    
    # 3. Company Stats
    cur.execute("SELECT COUNT(*), COUNT(CASE WHEN active THEN 1 END) FROM companies")
    total_companies, active_companies = cur.fetchone()
    
    print(f"\n📈 ACTIVITY (Last 24h)")
    print(f"  New Jobs:          {new_jobs}")
    print(f"  Companies Active:  {active_companies_24h}")
    
    print(f"\n🌍 TOTALS")
    print(f"  Total Jobs:        {total_jobs}")
    print(f"  Active Jobs:       {active_jobs}")
    print(f"  Total Companies:   {total_companies}")
    print(f"  Tracked Active:    {active_companies}")
    
    # 4. By Source/ATS (if strictly recorded in jobs or inferable)
    # Usually 'source' column holds this or we look at company.ats_provider
    print(f"\n🏭 JOBS BY ATS (Last 24h)")
    
    cur.execute("""
        SELECT c.ats_provider, COUNT(j.job_id)
        FROM jobs j
        JOIN companies c ON j.company = c.name
        WHERE j.date_posted >= NOW() - INTERVAL '24 hours'
        GROUP BY c.ats_provider
        ORDER BY COUNT(j.job_id) DESC
        LIMIT 10
    """)
    
    rows = cur.fetchall()
    if rows:
        for ats, count in rows:
            print(f"  {ats or 'Unknown'}: {count}")
    else:
        print("  (No jobs found in last 24h)")

    conn.close()

if __name__ == "__main__":
    try:
        generate_report()
    except Exception as e:
        print(f"Error generating report: {e}")
