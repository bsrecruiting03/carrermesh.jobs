import psycopg2
import os
import sys

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@127.0.0.1:5433/job_board")

def init_db():
    print(f"🚀 Initializing Database at {DATABASE_URL}")
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        
        # 1. Companies
        print("🔨 Table: companies")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                domain TEXT,
                career_page_url TEXT,
                ats_url TEXT UNIQUE,
                ats_provider TEXT,
                active BOOLEAN DEFAULT TRUE,
                last_scraped_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                consecutive_failures INTEGER DEFAULT 0,
                last_failure_at TIMESTAMP,
                circuit_open_until TIMESTAMP,
                last_success_at TIMESTAMP
            );
        """)
        
        # 2. Jobs
        print("🔨 Table: jobs")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                title TEXT,
                company TEXT,
                location TEXT,
                job_description TEXT,
                job_link TEXT,
                source TEXT,
                date_posted TIMESTAMP,
                is_remote BOOLEAN,
                work_mode TEXT,
                seniority TEXT,
                department TEXT,
                posted_bucket TEXT,
                ingested_at DATE,
                salary_min REAL,
                salary_max REAL,
                salary_currency TEXT,
                visa_sponsorship TEXT,
                visa_confidence REAL,
                normalized_location TEXT,
                city TEXT,
                state TEXT,
                country TEXT
            );
        """)
        
        # 3. Raw Jobs
        print("🔨 Table: raw_jobs")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_jobs (
                job_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                raw_payload JSONB NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            );
        """)
        
        # 4. Job Enrichment
        print("🔨 Table: job_enrichment")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS job_enrichment (
                job_id TEXT PRIMARY KEY,
                tech_languages TEXT,
                tech_frameworks TEXT,
                tech_cloud TEXT,
                tech_data TEXT,
                tech_tools TEXT,
                experience_min INTEGER,
                experience_max INTEGER,
                education TEXT,
                clearance TEXT,
                natural_languages TEXT,
                job_summary TEXT,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            );
        """)
        
        # 5. Job Search (Projection)
        print("🔨 Table: job_search")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS job_search (
                job_id TEXT PRIMARY KEY,
                company_id TEXT,
                title TEXT NOT NULL,
                location TEXT,
                work_mode TEXT,
                experience_min INTEGER,
                experience_max INTEGER,
                tech_stack_text TEXT,
                job_summary TEXT,
                date_posted TIMESTAMP,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                search_vector TSVECTOR,
                salary_min REAL,
                salary_max REAL,
                salary_currency TEXT,
                visa_sponsorship TEXT
            );
        """)
        
        # 6. workday_fingerprints
        print("🔨 Table: workday_fingerprints")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS workday_fingerprints (
                company_slug TEXT PRIMARY KEY,
                career_url TEXT NOT NULL,
                endpoint_url TEXT NOT NULL,
                method TEXT NOT NULL,
                headers JSONB NOT NULL,
                payload_template JSONB NOT NULL,
                tenant TEXT,
                verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active'
            );
        """)

        print("✅ Base Schema Initialized.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
