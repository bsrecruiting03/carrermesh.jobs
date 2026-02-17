
import psycopg2
import os

DB_URL = "postgresql://postgres:postgres@localhost:5433/job_board"

def update_schema():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    print("Updating job_enrichment table schema...")
    
    # Add new columns if they don't exist
    commands = [
        "ALTER TABLE job_enrichment ADD COLUMN IF NOT EXISTS seniority_tier TEXT;",
        "ALTER TABLE job_enrichment ADD COLUMN IF NOT EXISTS seniority_level INTEGER;",
        "ALTER TABLE job_enrichment ADD COLUMN IF NOT EXISTS education_level TEXT;",
        "ALTER TABLE job_enrichment ADD COLUMN IF NOT EXISTS certifications TEXT;",
        "ALTER TABLE job_enrichment ADD COLUMN IF NOT EXISTS soft_skills TEXT;"
    ]
    
    for cmd in commands:
        try:
            cur.execute(cmd)
            print(f"Executed: {cmd}")
        except Exception as e:
            print(f"Error executing {cmd}: {e}")
            conn.rollback()
    
    conn.commit()
    print("Schema update complete.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    update_schema()
