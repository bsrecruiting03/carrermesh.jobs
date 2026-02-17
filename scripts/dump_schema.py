import sys
import os
import psycopg2
import time

# Add root to python path to find modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from us_ats_jobs.db.database import get_db_connection

def dump_schema(table_name):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get Columns
        print(f"\n--- SCHEMA: {table_name} ---")
        cur.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{table_name}' 
            ORDER BY ordinal_position
        """)
        cols = cur.fetchall()
        for c in cols:
            print(f"  {c[0]} ({c[1]})")
            
        conn.close()
    except Exception as e:
        print(f"Error dumping {table_name}: {e}")

if __name__ == "__main__":
    print("Starting Schema Dump...")
    time.sleep(1)
    dump_schema('jobs')
    dump_schema('job_enrichment')
    dump_schema('job_skills')
    print("\nDone.")
