"""
Parallel Job Skills Backfill Script
===================================

Multi-worker version for faster backfill processing.

Usage:
    python scripts/backfill_job_skills_parallel.py --workers 12 --batch-size 1000
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import psycopg2
from psycopg2.extras import execute_batch
from typing import List, Dict, Tuple
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from us_ats_jobs.intelligence.skills_db import SkillExtractorDB, ExtractedSkill
import time
from datetime import datetime

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/job_board")

def process_job_batch_worker(worker_id: int, job_batch: List[Tuple], db_url: str) -> Dict:
    """
    Worker function to process a batch of jobs.
    Each worker has its own database connection and skill extractor.
    
    Args:
        worker_id: Worker identifier
        job_batch: List of (job_id, job_description, job_title) tuples
        db_url: Database connection string
    
    Returns:
        Dict with statistics
    """
    # Each worker gets its own connection
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    
    # Parse DB config from URL for SkillExtractor
    # Format: postgresql://user:pass@host:port/dbname
    parts = db_url.replace('postgresql://', '').split('@')
    user_pass = parts[0].split(':')
    host_port_db = parts[1].split('/')
    host_port = host_port_db[0].split(':')
    
    db_config = {
        'host': host_port[0],
        'port': int(host_port[1]),
        'database': host_port_db[1],
        'user': user_pass[0],
        'password': user_pass[1]
    }
    
    # Create skill extractor for this worker
    extractor = SkillExtractorDB(db_config)
    
    job_skills_data = []
    skill_ids_updates = []
    skills_extracted = 0
    
    for idx, (job_id, description, title) in enumerate(job_batch):
        # Combine title and description for skill extraction
        text = f"{title}\n\n{description}" if title and description else (title or description or "")
        
        if not text:
            continue
        
        # Extract skills
        skills = extractor.extract(text)
        
        if skills:
            skills_extracted += len(skills)
            
            # Prepare job_skills inserts
            for skill in skills:
                job_skills_data.append((
                    job_id,
                    skill.skill_id,
                    'description',  # extraction_source
                    skill.confidence,
                    skill.matched_synonym
                ))
            
            # Prepare job_enrichment update
            skill_ids = [s.skill_id for s in skills]
            skill_ids_updates.append((skill_ids, len(skill_ids), job_id))
    
    # Batch insert job_skills
    if job_skills_data:
        execute_batch(cur, """
            INSERT INTO job_skills (job_id, skill_id, extraction_source, extraction_confidence, matched_synonym)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (job_id, skill_id) DO NOTHING
        """, job_skills_data, page_size=500)
    
    # Batch update job_enrichment
    if skill_ids_updates:
        execute_batch(cur, """
            UPDATE job_enrichment
            SET skill_ids = %s,
                extracted_skill_count = %s
            WHERE job_id = %s
        """, skill_ids_updates, page_size=500)
    
    conn.commit()
    cur.close()
    conn.close()
    extractor.close()
    
    return {
        'worker_id': worker_id,
        'jobs_processed': len(job_batch),
        'skills_extracted': skills_extracted,
        'job_skills_inserted': len(job_skills_data)
    }


def get_jobs_to_process(conn, batch_size: int, offset: int) -> List[Tuple]:
    """Fetch a batch of jobs to process"""
    cur = conn.cursor()
    
    cur.execute("""
        SELECT j.job_id, j.job_description, j.title
        FROM jobs j
        WHERE j.job_description IS NOT NULL
        ORDER BY j.ingested_at DESC
        LIMIT %s OFFSET %s
    """, (batch_size, offset))
    
    jobs = cur.fetchall()
    cur.close()
    
    return jobs


def main():
    parser = argparse.ArgumentParser(description='Backfill job skills using MIND ontology (Parallel)')
    parser.add_argument('--workers', type=int, default=12, help='Number of parallel workers (default: 12)')
    parser.add_argument('--batch-size', type=int, default=1000, help='Jobs per batch (default: 1000)')
    parser.add_argument('--start-from', type=int, default=0, help='Starting offset (for resume)')
    parser.add_argument('--limit', type=int, default=None, help='Maximum jobs to process (optional)')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print(f"Job Skills Backfill Script (Parallel - {args.workers} workers)")
    print("=" * 70)
    
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Get total job count
    cur.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cur.fetchone()[0]
    
    jobs_to_process = args.limit if args.limit else (total_jobs - args.start_from)
    
    print(f"\nTotal jobs in database: {total_jobs:,}")
    print(f"Number of workers: {args.workers}")
    print(f"Batch size per worker: {args.batch_size}")
    print(f"Starting from offset: {args.start_from:,}")
    print(f"Jobs to process: {jobs_to_process:,}")
    
    # Calculate super-batches (one per worker)
    super_batch_size = args.batch_size * args.workers
    total_super_batches = (jobs_to_process + super_batch_size - 1) // super_batch_size
    
    print(f"Super-batch size (all workers): {super_batch_size:,}")
    print(f"Total super-batches: {total_super_batches}")
    print()
    
    start_time = time.time()
    total_skills_extracted = 0
    total_jobs_processed = 0
    
    # Process in super-batches
    for super_batch_idx in range(total_super_batches):
        super_batch_offset = args.start_from + (super_batch_idx * super_batch_size)
        
        # Fetch jobs for this super-batch
        super_batch_jobs = get_jobs_to_process(conn, super_batch_size, super_batch_offset)
        
        if not super_batch_jobs:
            break
        
        # Split super-batch into worker batches
        worker_batches = []
        jobs_per_worker = len(super_batch_jobs) // args.workers
        remainder = len(super_batch_jobs) % args.workers
        
        start_idx = 0
        for worker_id in range(args.workers):
            # Distribute remainder across first workers
            worker_batch_size = jobs_per_worker + (1 if worker_id < remainder else 0)
            end_idx = start_idx + worker_batch_size
            
            if start_idx < len(super_batch_jobs):
                worker_batches.append((worker_id, super_batch_jobs[start_idx:end_idx], DATABASE_URL))
            
            start_idx = end_idx
        
        print(f"Super-batch {super_batch_idx + 1}/{total_super_batches}: Processing {len(super_batch_jobs):,} jobs with {len(worker_batches)} workers...")
        
        # Process in parallel
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            # Submit all worker tasks
            future_to_worker = {
                executor.submit(process_job_batch_worker, worker_id, batch, db_url): worker_id
                for worker_id, batch, db_url in worker_batches
            }
            
            # Collect results
            batch_skills = 0
            batch_jobs = 0
            
            for future in as_completed(future_to_worker):
                result = future.result()
                batch_skills += result['skills_extracted']
                batch_jobs += result['jobs_processed']
                print(f"  Worker {result['worker_id']:2d}: {result['jobs_processed']:4d} jobs, {result['skills_extracted']:5d} skills")
        
        total_skills_extracted += batch_skills
        total_jobs_processed += batch_jobs
        
        elapsed = time.time() - start_time
        jobs_per_sec = total_jobs_processed / elapsed if elapsed > 0 else 0
        remaining_jobs = jobs_to_process - total_jobs_processed
        eta_seconds = remaining_jobs / jobs_per_sec if jobs_per_sec > 0 else 0
        
        print(f"  ✓ Super-batch complete: {batch_skills:,} skills ({batch_skills/len(super_batch_jobs):.1f} avg/job)")
        print(f"  Progress: {total_jobs_processed:,}/{jobs_to_process:,} ({100*total_jobs_processed/jobs_to_process:.1f}%)")
        print(f"  Speed: {jobs_per_sec:.1f} jobs/sec, ETA: {eta_seconds/3600:.1f} hours")
        print()
    
    # Final summary
    elapsed = time.time() - start_time
    
    cur.close()
    conn.close()
    
    print("=" * 70)
    print("BACKFILL COMPLETE")
    print("=" * 70)
    print(f"Total jobs processed: {total_jobs_processed:,}")
    print(f"Total skills extracted: {total_skills_extracted:,}")
    print(f"Average skills per job: {total_skills_extracted/total_jobs_processed:.2f}")
    print(f"Total time: {elapsed/3600:.2f} hours")
    print(f"Processing speed: {total_jobs_processed/elapsed:.1f} jobs/second")
    print()
    print("✓ Job skills backfill completed successfully!")


if __name__ == '__main__':
    main()
