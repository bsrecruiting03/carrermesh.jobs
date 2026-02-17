import sqlite3
import psycopg2
import os
import sys

# Config
SQLITE_DB = "us_ats_jobs/db/jobs.db"
# Use the URL found in database.py
PG_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/job_board")

def check_counts():
    print(f"🕵️  Checking Migration Status...")
    
    # 1. Check SQLite
    sqlite_counts = {}
    if os.path.exists(SQLITE_DB):
        try:
            conn = sqlite3.connect(SQLITE_DB)
            cursor = conn.cursor()
            for table in ["companies", "jobs", "job_enrichment", "raw_jobs"]:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    sqlite_counts[table] = cursor.fetchone()[0]
                except:
                    sqlite_counts[table] = "N/A (Table missing)"
            conn.close()
        except Exception as e:
            print(f"⚠️  SQLite Error: {e}")
    else:
        print(f"⚠️  SQLite DB not found at {SQLITE_DB}")
    
    # 2. Check Postgres
    pg_counts = {}
    try:
        conn = psycopg2.connect(PG_URL)
        cursor = conn.cursor()
        for table in ["companies", "jobs", "job_enrichment", "raw_jobs"]:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                pg_counts[table] = cursor.fetchone()[0]
            except Exception as e:
                # Table might not exist
                pg_counts[table] = "N/A (Table missing)"
        conn.close()
    except Exception as e:
        print(f"❌ Postgres Error: {e}")
        print("   (Is the database running on port 5433?)")

    # 3. Report
    print("\n📊 Database Comparison:")
    print(f"{'Table':<20} | {'SQLite':<15} | {'Postgres':<15}")
    print("-" * 56)
    for table in ["companies", "jobs", "job_enrichment", "raw_jobs"]:
        s_val = sqlite_counts.get(table, 0)
        p_val = pg_counts.get(table, 0)
        print(f"{table:<20} | {str(s_val):<15} | {str(p_val):<15}")

if __name__ == "__main__":
    check_counts()
