
import sys
import os
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import concurrent.futures
from tqdm import tqdm
import time
import re

# Add root path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from us_ats_jobs.intelligence.skills import SkillExtractor
from us_ats_jobs.intelligence.qualifications import QualificationsExtractor
from api.config import settings

# Configuration
BATCH_SIZE = 100  # Smaller batch size per worker for smoother progress updates
WORKERS = 8
DB_URL = settings.database_url

def get_db_connection():
    return psycopg2.connect(DB_URL)

def extract_experience(text: str):
    if not text: return None
    match = re.search(r'(\d+)\s*(?:\+)?\s*(?:year|yr)', text, re.IGNORECASE)
    if match:
        try:
            val = int(match.group(1))
            return val if val < 50 else None
        except: return None
    return None

def process_batch(jobs_batch):
    """
    Worker function to process a list of (job_id, title, description).
    Opening a new DB connection per worker is safer for multiprocessing.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Initialize separate extractors per process to avoid shared state issues
    skill_extractor = SkillExtractor()
    qual_extractor = QualificationsExtractor()
    
    enrichment_data = []
    
    try:
        for job in jobs_batch:
            job_id, title, description = job
            
            # --- 1. SKILLS ---
            extracted_skills = skill_extractor.extract(description)
            skill_summary = skill_extractor.get_structured_summary(extracted_skills)
            
            languages = ", ".join(skill_summary.get("Languages", []))
            frontend = ", ".join(skill_summary.get("Frontend", []))
            backend = ", ".join(skill_summary.get("Backend", []))
            mobile = ", ".join(skill_summary.get("Mobile", []))
            data_infra = ", ".join(skill_summary.get("Data & Infrastructure", []))
            devops = ", ".join(skill_summary.get("DevOps", []))
            testing = ", ".join(skill_summary.get("Testing", []))
            
            tech_languages = languages
            tech_frameworks = ", ".join(filter(None, [frontend, backend, mobile]))
            tech_cloud = devops
            tech_tools = ", ".join(filter(None, [data_infra, testing]))
            
            # --- 2. QUALIFICATIONS ---
            # This calls the UPDATED extract_all which creates corrected seniority
            qual_result = qual_extractor.extract_all(title, description)
            
            # --- 3. EXPERIENCE ---
            exp_years = extract_experience(description)
            
            enrichment_data.append((
                job_id,
                None, # summary
                tech_languages,
                tech_frameworks,
                tech_cloud,
                tech_tools,
                exp_years,
                qual_result.seniority_tier,
                qual_result.seniority_level,
                qual_result.education_level,
                ", ".join(qual_result.certifications),
                ", ".join(qual_result.soft_skills),
                datetime.now()
            ))
        
        # Upsert
        upsert_query = """
            INSERT INTO job_enrichment (
                job_id, summary, 
                tech_languages, tech_frameworks, tech_cloud, tech_tools, 
                experience_years, 
                seniority_tier, seniority_level, education_level, certifications, soft_skills,
                last_enriched_at
            ) VALUES %s
            ON CONFLICT (job_id) DO UPDATE SET
                tech_languages = EXCLUDED.tech_languages,
                tech_frameworks = EXCLUDED.tech_frameworks,
                tech_cloud = EXCLUDED.tech_cloud,
                tech_tools = EXCLUDED.tech_tools,
                experience_years = EXCLUDED.experience_years,
                seniority_tier = EXCLUDED.seniority_tier,
                seniority_level = EXCLUDED.seniority_level,
                education_level = EXCLUDED.education_level,
                certifications = EXCLUDED.certifications,
                soft_skills = EXCLUDED.soft_skills,
                last_enriched_at = EXCLUDED.last_enriched_at
        """
        
        execute_values(cur, upsert_query, enrichment_data)
        conn.commit()
        return len(enrichment_data)
        
    except Exception as e:
        print(f"Worker Error: {e}")
        conn.rollback()
        return 0
    finally:
        cur.close()
        conn.close()

def main():
    print(f"Starting Mass Enrichment with {WORKERS} workers...")
    
    # 1. Fetch Target Jobs
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("Fetching target jobs (Latest 5000 to apply new logic)...")
    # Fetch latest 5000 jobs to re-process and apply new seniority/skill logic
    cur.execute("""
        SELECT j.job_id, j.title, j.job_description 
        FROM jobs j
        WHERE j.job_description IS NOT NULL
        AND LENGTH(j.job_description) > 100
        ORDER BY j.date_posted DESC
        LIMIT 5000
    """)
    
    all_jobs = cur.fetchall()
    total_jobs = len(all_jobs)
    cur.close()
    conn.close()
    
    print(f"Found {total_jobs} jobs pending enrichment.")
    
    if total_jobs == 0:
        return

    # 2. Chunk Data
    print(f"Chunking into batches of {BATCH_SIZE}...")
    batches = [all_jobs[i:i + BATCH_SIZE] for i in range(0, len(all_jobs), BATCH_SIZE)]
    
    # 3. Parallel Execution
    print("Launching workers...")
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=WORKERS) as executor:
        # Submit all batches
        futures = [executor.submit(process_batch, batch) for batch in batches]
        
        # Monitor progress
        completed_count = 0
        with tqdm(total=total_jobs, unit="jobs") as pbar:
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                pbar.update(result)
                completed_count += result
                
    print(f"\nCompleted! Processed {completed_count} jobs.")

if __name__ == "__main__":
    main()
