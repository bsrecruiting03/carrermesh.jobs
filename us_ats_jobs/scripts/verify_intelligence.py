import sys
import os
import sqlite3
from datetime import date

# Add parent path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import db.database as database

def verify_intelligence():
    print("🧪 Verifying Intelligence Layer...")
    
    # 1. Insert a test job
    test_job = {
        "job_id": "test_intel_001",
        "title": "Senior Software Engineer (Remote)",
        "company": "TestCorp",
        "location": "San Francisco, CA",
        "job_description": "We are looking for a remote senior engineer to lead our backend team.",
        "job_link": "https://example.com",
        "source": "test",
        "date_posted": date.today().isoformat()
    }
    
    print("  Inserting test job...")
    database.insert_jobs([test_job])
    
    # 2. Query the job directly to check derived fields
    with database.get_connection() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE job_id = 'test_intel_001'").fetchone()
        row_dict = dict(row)
        
        print(f"  Existing columns: {row_dict.keys()}")
        
        # Check specific fields
        print(f"  - is_remote: {row_dict.get('is_remote')} (Expected: 1)")
        print(f"  - seniority: {row_dict.get('seniority')} (Expected: 'senior')")
        print(f"  - department: {row_dict.get('department')} (Expected: 'engineering')")
        print(f"  - posted_bucket: {row_dict.get('posted_bucket')} (Expected: 'last_24h')")

        if row_dict.get('is_remote') == 1 and row_dict.get('seniority') == 'senior':
             print("  ✅ Inference Logic: PASS")
        else:
             print("  ❌ Inference Logic: FAIL")

    # 3. Test Query Function
    print("\n  Testing get_remote_senior_jobs()...")
    results = database.get_remote_senior_jobs(days=1, limit=5)
    print(f"  Found {len(results)} jobs (including our test job).")
    
    found_test = any(r['title'] == "Senior Software Engineer (Remote)" for r in results)
    if found_test:
        print("  ✅ Query Logic: PASS")
    else:
        print("  ❌ Query Logic: FAIL (Did not find test job)")

if __name__ == "__main__":
    verify_intelligence()
