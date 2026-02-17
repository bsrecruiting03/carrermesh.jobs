"""
Backfill Job Skills Script
===========================

Re-processes all existing jobs to extract skills using the new MIND ontology
and populate the job_skills and job_enrichment.skill_ids columns.

This should be run after importing the MIND ontology into the database.

Usage:
    python scripts/backfill_job_skills.py --batch-size 1000 --start-from 0

Arguments:
    --batch-size: Number of jobs to process per batch (default: 1000)
    --start-from: Job offset to start from (for resuming, default: 0)
    --limit: Max number of jobs to process (default: all)
    --dry-run: Preview without making changes
"""

import psycopg2
from psycopg2.extras import execute_batch
import argparse
from typing import List, Dict, Tuple
import sys
import os

# Add parent directory to path to import intelligence modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from us_ats_jobs.intelligence.skills_db import SkillExtractorDB, ExtractedSkill

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "job_board",
    "user": "postgres",
    "password": "postgres"
}


class JobSkillBackfiller:
    """Backfills job_skills table from existing job descriptions"""
    
    def __init__(self, db_config: dict):
        self.conn = psycopg2.connect(**db_config)
        self.extractor = SkillExtractorDB(db_config)
        
        self.total_processed = 0
        self.total_skills_extracted = 0
        self.jobs_with_skills = 0
        self.jobs_without_skills = 0
    
    def get_job_batch(self, offset: int, limit: int) -> List[Tuple]:
        """Fetch a batch of jobs to process"""
        cur = self.conn.cursor()
        
        cur.execute("""
            SELECT 
                j.job_id,
                j.title,
                j.job_description
            FROM jobs j
            WHERE j.job_description IS NOT NULL
            ORDER BY j.ingested_at DESC
            OFFSET %s
            LIMIT %s
        """, (offset, limit))
        
        jobs = cur.fetchall()
        cur.close()
        
        return jobs
    
    def extract_skills_from_job(self, job_id: str, title: str, 
                               description: str) -> List[ExtractedSkill]:
        """Extract skills from a single job"""
        # Combine title and description for extraction
        full_text = f"{title}\n\n{description}"
        
        # Extract using database-backed extractor
        skills = self.extractor.extract_with_context(full_text)
        
        return skills
    
    def save_job_skills(self, job_id: str, skills: List[ExtractedSkill]):
        """Save extracted skills to database"""
        if not skills:
            return
        
        cur = self.conn.cursor()
        
        # Delete existing skills for this job (in case of re-run)
        cur.execute("DELETE FROM job_skills WHERE job_id = %s", (job_id,))
        
        # Insert new job_skills records
        job_skill_data = [
            (
                job_id,
                skill.skill_id,
                'description',  # extraction_source
                skill.confidence,
                skill.matched_synonym
            )
            for skill in skills
        ]
        
        execute_batch(cur, """
            INSERT INTO job_skills (
                job_id, skill_id, extraction_source, 
                extraction_confidence, matched_synonym
            )
            VALUES (%s, %s, %s, %s, %s)
        """, job_skill_data)
        
        # Update job_enrichment table
        skill_ids = [s.skill_id for s in skills]
        
        cur.execute("""
            UPDATE job_enrichment
            SET skill_ids = %s,
                extracted_skill_count = %s
            WHERE job_id = %s
        """, (skill_ids, len(skill_ids), job_id))
        
        self.conn.commit()
        cur.close()
    
    def process_batch(self, jobs: List[Tuple], batch_num: int, 
                     total_batches: int, dry_run: bool = False):
        """Process a batch of jobs"""
        print(f"\nBatch {batch_num}/{total_batches}: Processing {len(jobs)} jobs...")
        
        batch_skills_count = 0
        batch_with_skills = 0
        
        for i, (job_id, title, description) in enumerate(jobs):
            # Extract skills
            skills = self.extract_skills_from_job(job_id, title, description)
            
            if skills:
                batch_skills_count += len(skills)
                batch_with_skills += 1
                
                if not dry_run:
                    self.save_job_skills(job_id, skills)
            
            # Progress indicator
            if (i + 1) % 100 == 0:
                print(f"  Processed {i + 1}/{len(jobs)} jobs in batch...")
        
        self.total_processed += len(jobs)
        self.total_skills_extracted += batch_skills_count
        self.jobs_with_skills += batch_with_skills
        self.jobs_without_skills += (len(jobs) - batch_with_skills)
        
        avg_skills = batch_skills_count / len(jobs) if jobs else 0
        print(f"  ✓ Batch complete: {batch_skills_count} skills extracted "
              f"(avg: {avg_skills:.1f} skills/job)")
    
    def print_summary(self):
        """Print backfill summary statistics"""
        print("\n" + "=" * 70)
        print("BACKFILL SUMMARY")
        print("=" * 70)
        print(f"Total jobs processed: {self.total_processed:,}")
        print(f"Jobs with skills: {self.jobs_with_skills:,}")
        print(f"Jobs without skills: {self.jobs_without_skills:,}")
        print(f"Total skills extracted: {self.total_skills_extracted:,}")
        
        if self.total_processed > 0:
            avg_per_job = self.total_skills_extracted / self.total_processed
            coverage_pct = (self.jobs_with_skills / self.total_processed) * 100
            print(f"\nAverage skills per job: {avg_per_job:.1f}")
            print(f"Coverage: {coverage_pct:.1f}%")
    
    def close(self):
        """Close connections"""
        self.extractor.close()
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Backfill job_skills table from existing job descriptions'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Number of jobs to process per batch (default: 1000)'
    )
    parser.add_argument(
        '--start-from',
        type=int,
        default=0,
        help='Job offset to start from (default: 0)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of jobs to process (default: all)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview without making database changes'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Job Skills Backfill Script")
    print("=" * 70)
    
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No database changes will be made\n")
    
    # Get total job count
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM jobs WHERE job_description IS NOT NULL")
    total_jobs = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    print(f"\nTotal jobs in database: {total_jobs:,}")
    print(f"Batch size: {args.batch_size}")
    print(f"Starting from offset: {args.start_from}")
    
    # Calculate batches
    jobs_to_process = args.limit if args.limit else (total_jobs - args.start_from)
    total_batches = (jobs_to_process + args.batch_size - 1) // args.batch_size
    
    print(f"Jobs to process: {jobs_to_process:,}")
    print(f"Total batches: {total_batches}")
    
    # Initialize backfiller
    backfiller = JobSkillBackfiller(DB_CONFIG)
    
    try:
        offset = args.start_from
        batch_num = 1
        
        while True:
            # Fetch batch
            jobs = backfiller.get_job_batch(offset, args.batch_size)
            
            if not jobs:
                break
            
            # Process batch
            backfiller.process_batch(jobs, batch_num, total_batches, args.dry_run)
            
            # Update offset
            offset += len(jobs)
            batch_num += 1
            
            # Check limit
            if args.limit and offset >= (args.start_from + args.limit):
                break
        
        # Print summary
        backfiller.print_summary()
        
        if not args.dry_run:
            print("\n" + "=" * 70)
            print("✓ Backfill completed successfully!")
            print("=" * 70)
            print("\nNext steps:")
            print("1. Verify skill extraction quality:")
            print("   SELECT * FROM skill_usage_stats LIMIT 20;")
            print("2. Test hierarchical search:")
            print("   Run search queries and compare results")
            print("3. Update job ingestion pipeline to use new extractor")
        else:
            print("\n" + "=" * 70)
            print("Dry run complete - no changes made")
            print("=" * 70)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        print(f"Processed {backfiller.total_processed} jobs before interruption")
        print("You can resume by running with --start-from {}".format(
            args.start_from + backfiller.total_processed
        ))
    
    except Exception as e:
        print(f"\n❌ Error during backfill: {e}")
        raise
    
    finally:
        backfiller.close()


if __name__ == '__main__':
    main()
