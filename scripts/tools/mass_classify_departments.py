
import sys
import os
import psycopg2
from psycopg2.extras import execute_values
import concurrent.futures
from tqdm import tqdm

# Add root path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from us_ats_jobs.intelligence.classify_departments import DepartmentClassifier
from api.config import settings

# Configuration
BATCH_SIZE = 2000
WORKERS = 10
DB_URL = settings.database_url

def get_db_connection():
    return psycopg2.connect(DB_URL)

def process_batch(jobs_batch):
    conn = get_db_connection()
    cur = conn.cursor()
    clf = DepartmentClassifier()
    
    updates = []
    
    try:
        for job_id, title in jobs_batch:
            category, subcategory = clf.classify(title)
            updates.append((category, subcategory, job_id))
        
        # Bulk Update using execute_values
        # We use a temporary table approach or CASE statement? 
        # Actually execute_values with UPDATE... FROM VALUES is cleanest for massive updates
        
        update_query = """
            UPDATE jobs AS j
            SET department_category = v.category,
                department_subcategory = v.subcategory
            FROM (VALUES %s) AS v(category, subcategory, job_id)
            WHERE j.job_id = v.job_id
        """
        
        execute_values(cur, update_query, updates)
        conn.commit()
        return len(updates)
        
    except Exception as e:
        print(f"Worker Error: {e}")
        conn.rollback()
        return 0
    finally:
        cur.close()
        conn.close()

def main():
    print(f"Starting Mass Department Classification ({WORKERS} workers)...")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("Fetching all job titles...")
    cur.execute("SELECT job_id, title FROM jobs WHERE department_category IS NULL")
    all_jobs = cur.fetchall()
    total_jobs = len(all_jobs)
    cur.close()
    conn.close()
    
    print(f"Found {total_jobs} unclassified jobs.")
    
    if total_jobs == 0:
        return

    # Chunk Data
    batches = [all_jobs[i:i + BATCH_SIZE] for i in range(0, len(all_jobs), BATCH_SIZE)]
    
    # Parallel Execution
    print("Launching workers...")
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(process_batch, batch) for batch in batches]
        
        completed_count = 0
        with tqdm(total=total_jobs, unit="jobs") as pbar:
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                pbar.update(result)
                completed_count += result
                
    print(f"\nCompleted! Classified {completed_count} jobs.")

if __name__ == "__main__":
    main()
