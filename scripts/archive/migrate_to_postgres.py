import sqlite3
import psycopg2
from psycopg2.extras import execute_batch, Json
import os
import sys
import json
from pathlib import Path

# Default config
SQLITE_DB = "us_ats_jobs/db/jobs.db"
DEFAULT_PG_URL = "postgresql://postgres:postgres@localhost:5432/job_board"

def get_sqlite_conn(db_path):
    if not os.path.exists(db_path):
        print(f"❌ SQLite DB not found at: {db_path}")
        sys.exit(1)
    return sqlite3.connect(db_path)

def get_pg_conn(pg_url):
    try:
        return psycopg2.connect(pg_url)
    except Exception as e:
        print(f"❌ Failed to connect to Postgres: {e}")
        print(f"   URL used: {pg_url}")
        sys.exit(1)

def create_schema(pg_conn):
    print("🔨 Creating Postgres Schema...")
    with pg_conn.cursor() as cur:
        # 1. Companies
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
        
        # 3. Raw Jobs (JSONB)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_jobs (
                job_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                raw_payload JSONB NOT NULL,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            );
        """)
        
        # 4. Job Enrichment (JSONB potential, but keeping separate cols for now as per key plan)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS job_enrichment (
                job_id TEXT PRIMARY KEY,
                tech_languages TEXT,
                tech_frameworks TEXT,
                tech_cloud TEXT,
                tech_data TEXT,
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
        
        # 5. Workday Fingerprints (JSONB)
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

    pg_conn.commit()
    print("✅ Schema created.")

def clean_ts(val):
    """Convert empty string to None for Postgres timestamp compliance."""
    if not val:
        return None
    return val

def migrate_data(sqlite_db, pg_url):
    s_conn = get_sqlite_conn(sqlite_db)
    p_conn = get_pg_conn(pg_url)
    
    # Enable schema creation
    create_schema(p_conn)
    
    with s_conn, p_conn:
        s_cur = s_conn.cursor()
        p_cur = p_conn.cursor()
        
        # --- COMPANIES ---
        print("📦 Migrating Companies...")
        s_cur.execute("SELECT * FROM companies")
        rows = s_cur.fetchall()
        # Get column names
        cols = [description[0] for description in s_cur.description]
        
        # We need to map columns because order might differ or we have extra ID column
        # Postgres has SERIAL id, SQLite has INTEGER PRIMARY KEY AUTOINCREMENT
        # We will copy ID to preserve relationships
        
        pg_cols = ["id", "name", "domain", "career_page_url", "ats_url", "ats_provider", 
                   "active", "last_scraped_at", "created_at", "consecutive_failures",
                   "last_failure_at", "circuit_open_until", "last_success_at"]
                   
        data_to_insert = []
        for row in rows:
            row_dict = dict(zip(cols, row))
            data_to_insert.append((
                row_dict.get('id'),
                row_dict.get('name'),
                row_dict.get('domain'),
                row_dict.get('career_page_url'),
                row_dict.get('ats_url'),
                row_dict.get('ats_provider'),
                bool(row_dict.get('active')), # Convert 1/0 to bool
                clean_ts(row_dict.get('last_scraped_at')),
                clean_ts(row_dict.get('created_at')),
                row_dict.get('consecutive_failures'),
                clean_ts(row_dict.get('last_failure_at')),
                clean_ts(row_dict.get('circuit_open_until')),
                clean_ts(row_dict.get('last_success_at'))
            ))
            
        execute_batch(p_cur, """
            INSERT INTO companies (id, name, domain, career_page_url, ats_url, ats_provider, 
                                   active, last_scraped_at, created_at, consecutive_failures,
                                   last_failure_at, circuit_open_until, last_success_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING;
        """, data_to_insert)
        print(f"   Moved {len(data_to_insert)} companies.")
        
        # --- JOBS ---
        print("📦 Migrating Jobs...")
        s_cur.execute("SELECT * FROM jobs")
        rows = s_cur.fetchall()
        cols = [d[0] for d in s_cur.description]
        
        job_data = []
        for row in rows:
            d = dict(zip(cols, row))
            # Convert is_remote 1/0 to bool
            is_rem = d.get('is_remote')
            is_rem_bool = True if is_rem == 1 else False
            
            job_data.append((
                d.get('job_id'), d.get('title'), d.get('company'), d.get('location'),
                d.get('job_description'), d.get('job_link'), d.get('source'), clean_ts(d.get('date_posted')),
                is_rem_bool, d.get('work_mode'), d.get('seniority'), d.get('department'),
                d.get('posted_bucket'), clean_ts(d.get('ingested_at')), d.get('salary_min'), d.get('salary_max'),
                d.get('salary_currency'), d.get('visa_sponsorship'), d.get('visa_confidence'),
                d.get('normalized_location'), d.get('city'), d.get('state'), d.get('country')
            ))
            
        execute_batch(p_cur, """
            INSERT INTO jobs (job_id, title, company, location, job_description, job_link, source, date_posted,
                              is_remote, work_mode, seniority, department, posted_bucket, ingested_at,
                              salary_min, salary_max, salary_currency, visa_sponsorship, visa_confidence,
                              normalized_location, city, state, country)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (job_id) DO NOTHING;
        """, job_data)
        print(f"   Moved {len(job_data)} jobs.")
        
        # --- RAW JOBS ---
        print("📦 Migrating Raw Jobs...")
        s_cur.execute("SELECT * FROM raw_jobs")
        rows = s_cur.fetchall()
        cols = [d[0] for d in s_cur.description]
        
        raw_data = []
        for row in rows:
            d = dict(zip(cols, row))
            payload = d.get('raw_payload')
            # If payload is string, try parse to dict for Json wrapper, else let Postgres parse string to JSONB
            try:
                payload_dict = json.loads(payload)
                json_val = Json(payload_dict)
            except:
                json_val = payload # Fallback, Postgres will interpret string as JSONB literal id valid
            
            raw_data.append((
                d.get('job_id'), d.get('source'), json_val, clean_ts(d.get('fetched_at'))
            ))
            
        execute_batch(p_cur, """
            INSERT INTO raw_jobs (job_id, source, raw_payload, fetched_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (job_id) DO NOTHING;
        """, raw_data)
        print(f"   Moved {len(raw_data)} raw records.")

        # --- FINGERPRINTS ---
        print("📦 Migrating Fingerprints...")
        s_cur.execute("SELECT * FROM workday_fingerprints")
        rows = s_cur.fetchall()
        if rows:
            cols = [d[0] for d in s_cur.description]
            fp_data = []
            for row in rows:
                d = dict(zip(cols, row))
                # headers/template are text in sqlite, jsonb in postgres
                try:
                    h = Json(json.loads(d.get('headers', '{}')))
                    t = Json(json.loads(d.get('payload_template', '{}')))
                except:
                    h = "{}"
                    t = "{}"
                
                fp_data.append((
                    d.get('company_slug'), d.get('career_url'), d.get('endpoint_url'),
                    d.get('method'), h, t, d.get('tenant'), clean_ts(d.get('verified_at')), d.get('status')
                ))
            
            execute_batch(p_cur, """
                INSERT INTO workday_fingerprints 
                (company_slug, career_url, endpoint_url, method, headers, payload_template, tenant, verified_at, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (company_slug) DO NOTHING;
            """, fp_data)
            print(f"   Moved {len(fp_data)} fingerprints.")
        else:
            print("   No fingerprints to migrate.")

    print("\n🎉 Migration Complete!")

if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL", DEFAULT_PG_URL)
    migrate_data(SQLITE_DB, db_url)
