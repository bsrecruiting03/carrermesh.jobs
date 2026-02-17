
import sys
import os
import psycopg2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))

from api.config import settings

def add_missing_columns():
    conn = None
    try:
        print("Connecting to DB...")
        conn = psycopg2.connect(settings.database_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Checking 'job_enrichment' table...")
        
        # Check if tech_data exists
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='job_enrichment' AND column_name='tech_data';
        """)
        if not cur.fetchone():
            print("⚠️ 'tech_data' column MISSING. Adding it...")
            cur.execute("ALTER TABLE job_enrichment ADD COLUMN tech_data TEXT;")
            print("✅ Added 'tech_data' column.")
        else:
            print("✅ 'tech_data' column already exists.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    add_missing_columns()
