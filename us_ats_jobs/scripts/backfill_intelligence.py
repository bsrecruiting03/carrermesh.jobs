import sys
import os
from datetime import date

# Add parent path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import db.database as database

try:
    from intelligence.infer import (
        infer_remote, infer_seniority, infer_department, bucket_posted,
        extract_salary, infer_visa
    )
except ImportError:
    print("⚠️ Could not import intelligence module.")
    sys.exit(1)

def backfill():
    print("🔄 Starting Intelligence Backfill (Phase 1.6 - Refactor)...")
    
    # 1. Get all jobs using new helper
    try:
        jobs = database.get_all_jobs()
    except AttributeError:
        print("❌ database.get_all_jobs() not found. Did you update database.py?")
        return

    print(f"  Found {len(jobs)} jobs to backfill.")
    
    count = 0
    for job in jobs:
        # Extract fields safely
        desc = job.get("job_description") or ""
        title = job.get("title") or ""
        location = job.get("location") or ""
        date_posted = job.get("date_posted") or ""

        # Inference
        is_remote = infer_remote(location, desc)
        seniority = infer_seniority(title, desc)
        department = infer_department(title, desc)
        posted_bucket = bucket_posted(date_posted)
        salary_min, salary_max, salary_curr = extract_salary(desc)
        visa_sponsorship, visa_conf = infer_visa(desc)

        # Update using new helper
        database.update_job_fields(job["job_id"], {
            "is_remote": is_remote,
            "seniority": seniority,
            "department": department,
            "posted_bucket": posted_bucket,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": salary_curr,
            "visa_sponsorship": visa_sponsorship,
            "visa_confidence": visa_conf,
            # We can optionally update ingested_at if we want to "touch" the record
            # "ingested_at": date.today().isoformat()
        })
        count += 1
        
        if count % 500 == 0:
            print(f"  Processed {count} jobs...")

    print(f"  ✅ Backfill complete. Updated {count} jobs.")

def verify_sample():
    print("\n🔎 Verifying Sample Data (Top 5 w/ Salary)...")
    with database.get_connection() as conn:
        cursor = conn.execute("SELECT title, salary_min, salary_max, visa_sponsorship FROM jobs WHERE salary_min IS NOT NULL LIMIT 5")
        rows = cursor.fetchall()
        if not rows:
            print("  (No jobs with salary found in sample)")
        else:
            for r in rows:
                print(f"  - {r[0][:30]}... → ${r[1]}-${r[2]}, Visa: {r[3]}")

if __name__ == "__main__":
    backfill()
    verify_sample()
