
import psycopg2
import sys

def migrate_schema():
    print("🚀 Starting Schema Migration...")
    try:
        conn = psycopg2.connect(
            dbname="job_board",
            user="postgres",
            password="password",
            host="127.0.0.1",
            port="5433"
        )
        cur = conn.cursor()
        
        # 1. Add logo_url to companies
        print("Migrating 'companies' table...")
        cur.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS logo_url TEXT;")
        
        # 2. Add columns to job_search
        print("Migrating 'job_search' table...")
        cur.execute("ALTER TABLE job_search ADD COLUMN IF NOT EXISTS normalized_location TEXT;")
        cur.execute("ALTER TABLE job_search ADD COLUMN IF NOT EXISTS job_link TEXT;")
        cur.execute("ALTER TABLE job_search ADD COLUMN IF NOT EXISTS ingested_at TIMESTAMP;")
        cur.execute("ALTER TABLE job_search ADD COLUMN IF NOT EXISTS employment_type TEXT;")
        cur.execute("ALTER TABLE job_search ADD COLUMN IF NOT EXISTS skills TEXT[];")
        cur.execute("ALTER TABLE job_search ADD COLUMN IF NOT EXISTS logo_url TEXT;")

        conn.commit()
        print("✅ Schema Migration Successful!")
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    migrate_schema()
