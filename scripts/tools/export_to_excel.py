import sqlite3
import pandas as pd
import os

# Define database path
DB_PATH = os.path.join("us_ats_jobs", "db", "jobs.db")
OUTPUT_DIR = "output"

def export_data():
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        print("📊 Exporting Companies...")
        companies_df = pd.read_sql_query("SELECT * FROM companies", conn)
        companies_file = os.path.join(OUTPUT_DIR, "all_companies.xlsx")
        companies_df.to_excel(companies_file, index=False)
        print(f"✅ Saved {len(companies_df)} companies to {companies_file}")
        
        print("📊 Exporting Jobs...")
        jobs_df = pd.read_sql_query("SELECT * FROM jobs", conn)
        jobs_file = os.path.join(OUTPUT_DIR, "all_jobs.xlsx")
        jobs_df.to_excel(jobs_file, index=False)
        print(f"✅ Saved {len(jobs_df)} jobs to {jobs_file}")
        
    except Exception as e:
        print(f"❌ Error exporting data: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    export_data()
