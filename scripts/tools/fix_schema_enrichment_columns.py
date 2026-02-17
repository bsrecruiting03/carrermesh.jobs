
import sys
import os
import psycopg2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))

from api.config import settings

def fix_all_schema_columns():
    conn = None
    try:
        print("Connecting to DB...")
        conn = psycopg2.connect(settings.database_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Checking 'job_enrichment' table for missing columns...")
        
        # List of columns to check and their types
        columns_to_check = [
            ("experience_min", "INTEGER"),
            ("experience_max", "INTEGER"),
            ("education", "TEXT"),
            ("clearance", "TEXT"),
            ("natural_languages", "TEXT"),
            ("job_summary", "TEXT")
        ]
        
        for col_name, col_type in columns_to_check:
            cur.execute(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='job_enrichment' AND column_name='{col_name}';
            """)
            if not cur.fetchone():
                print(f"⚠️ '{col_name}' column MISSING. Adding it...")
                cur.execute(f"ALTER TABLE job_enrichment ADD COLUMN {col_name} {col_type};")
                print(f"✅ Added '{col_name}' column.")
            else:
                print(f"✅ '{col_name}' column already exists.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    fix_all_schema_columns()
