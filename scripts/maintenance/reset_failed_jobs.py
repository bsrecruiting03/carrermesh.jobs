#!/usr/bin/env python3
"""
Reset Failed Jobs Script
Resets all failed jobs to 'pending' status so they can be reprocessed
with the fixed schema and multi-key rotation system.
"""

import psycopg2
import os
from dotenv import load_dotenv

# Load environment
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, '.env'))

DATABASE_URL = os.getenv("DATABASE_URL")

def reset_failed_jobs():
    """Reset all failed jobs to pending for reprocessing"""
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    try:
        # Get count before reset
        cur.execute("SELECT COUNT(*) FROM jobs WHERE enrichment_status = 'failed'")
        failed_count = cur.fetchone()[0]
        
        print("\n" + "="*70)
        print("RESET FAILED JOBS")
        print("="*70 + "\n")
        
        print(f"Found {failed_count:,} failed jobs\n")
        
        if failed_count == 0:
            print("No failed jobs to reset!")
            return
        
        # Show user what will happen
        print("This will:")
        print("  1. Clear error logs")
        print("  2. Set status back to 'pending'")
        print("  3. Allow worker to retry with fixed system\n")
        
        response = input(f"Reset {failed_count:,} jobs? (yes/no): ").strip().lower()
        
        if response != 'yes':
            print("\nCancelled.")
            return
        
        # Reset the jobs
        print("\nResetting jobs...")
        cur.execute("""
            UPDATE jobs 
            SET 
                enrichment_status = 'pending',
                error_log = NULL
            WHERE enrichment_status = 'failed'
        """)
        
        conn.commit()
        
        print(f"✅ Successfully reset {failed_count:,} jobs to pending!\n")
        print("The worker will now reprocess these jobs with:")
        print("  ✓ Fixed database schema")
        print("  ✓ Corrected triggers")
        print("  ✓ 5-key rotation system")
        print("  ✓ Improved error handling\n")
        
        # Show updated stats
        cur.execute("SELECT COUNT(*) FROM jobs WHERE enrichment_status = 'pending'")
        pending = cur.fetchone()[0]
        
        print(f"Current queue: {pending:,} pending jobs")
        print(f"Processing rate: ~1,500 jobs/hour")
        print(f"Estimated completion: {pending/1500:.1f} hours\n")
        
        print("="*70 + "\n")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}\n")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    reset_failed_jobs()
