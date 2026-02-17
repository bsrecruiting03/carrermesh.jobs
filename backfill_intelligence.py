"""
Backfill script to populate new intelligence columns for existing jobs.
"""
import sys
import os
import sqlite3

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "us_ats_jobs")))

from intelligence.infer import infer_work_mode, infer_seniority, infer_department, bucket_posted, extract_salary, infer_visa
from utils.location_utils import normalize_location

def backfill():
    print("🚀 Starting backfill of intelligence data...")
    conn = sqlite3.connect("us_ats_jobs/db/jobs.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get jobs that need processing (where work_mode is NULL)
    cursor.execute("SELECT job_id, title, location, job_description, date_posted FROM jobs WHERE work_mode IS NULL OR normalized_location IS NULL")
    jobs = cursor.fetchall()
    print(f"Found {len(jobs)} jobs to update.")

    count = 0
    for job in jobs:
        title = job['title']
        desc = job['job_description'] or ""
        loc_raw = job['location'] or ""
        
        # 1. Work Mode
        work_mode = infer_work_mode(loc_raw, desc)
        is_remote = 1 if work_mode in ["remote", "hybrid"] else 0
        
        # 2. Location
        loc_data = normalize_location(loc_raw)
        
        # 3. Other Intelligence
        seniority = infer_seniority(title, desc)
        department = infer_department(title, desc)
        posted_bucket = bucket_posted(job['date_posted'])
        salary_min, salary_max, salary_curr = extract_salary(desc)
        visa_sponsorship, visa_conf = infer_visa(desc)

        conn.execute("""
            UPDATE jobs SET 
                work_mode = ?, 
                is_remote = ?,
                normalized_location = ?,
                city = ?,
                state = ?,
                country = ?,
                seniority = ?,
                department = ?,
                posted_bucket = ?,
                salary_min = ?,
                salary_max = ?,
                salary_currency = ?,
                visa_sponsorship = ?,
                visa_confidence = ?
            WHERE job_id = ?
        """, (
            work_mode, is_remote, loc_data['full'], loc_data['city'], loc_data['state'], loc_data['country'],
            seniority, department, posted_bucket, salary_min, salary_max, salary_curr,
            visa_sponsorship, visa_conf, job['job_id']
        ))
        
        count += 1
        if count % 500 == 0:
            conn.commit()
            print(f"Processed {count} jobs...")

    conn.commit()
    conn.close()
    print(f"✅ Success! Backfilled {count} jobs.")

if __name__ == "__main__":
    backfill()
