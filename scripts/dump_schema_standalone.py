import psycopg2
import os

# Hardcoded credentials from .env observation
DB_URL = "postgresql://postgres:password@localhost:5433/job_board"

def dump_schema(table_name):
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
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
    dump_schema('jobs')
    dump_schema('job_enrichment')
    dump_schema('job_skills')
