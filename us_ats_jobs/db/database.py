import os
import json
import datetime
import hashlib
import psycopg2
from psycopg2 import pool, extras
from psycopg2.extras import execute_batch, execute_values
from contextlib import contextmanager
import logging
from us_ats_jobs.intelligence.location_matcher import get_matcher

# Configuration
DEFAULT_DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
MIN_CONN = 1
MAX_CONN = 40  # Support 30+ workers

def get_db_config():
    """Returns database connection parameters as a dictionary."""
    from psycopg2.extensions import make_dsn, parse_dsn
    return parse_dsn(DATABASE_URL)

# Global Connection Pool
pg_pool = None

def init_pool():
    global pg_pool
    if pg_pool is None:
        try:
            pg_pool = psycopg2.pool.ThreadedConnectionPool(
                MIN_CONN, MAX_CONN, DATABASE_URL
            )
            print(f"Postgres Connection Pool initialized ({MIN_CONN}-{MAX_CONN} connections)")
        except Exception as e:
            print(f"Failed to initialize Postgres pool: {e}")
            raise

@contextmanager
def get_connection():
    if pg_pool is None:
        init_pool()
    
    conn = pg_pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        pg_pool.putconn(conn)

def create_tables():
    """
    Ensures tables exist. Ideally schema is managed by migration script,
    but this ensures safety for new installs.
    """
    # Schema creation is handled by migration script mostly.
    # We will just verify connection here.
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")

# -------- CORE INSERTION --------

def insert_jobs(jobs):
    if not jobs:
        return 0

    from datetime import date
    today_str = date.today().isoformat()

    # Pre-process jobs (Intelligence Layer logic replicated)
    # We assume 'jobs' passed here are raw dicts needing enrichment?
    # Actually, in original database.py, insert_jobs calls specific enrichment functions.
    # We need to preserve that logic or import it.
    
    # Import intelligence (lazy import to avoid circular dep if any)
    try:
        from us_ats_jobs.intelligence.infer import (
            infer_work_mode, infer_seniority, infer_department, bucket_posted,
            extract_salary, infer_visa, extract_all_enrichment
        )
        from us_ats_jobs.utils.location_utils import normalize_location
    except ImportError as e:
         print(f"⚠️ Intelligence module import failed: {e}")
         # Mock functions if ensuring no crash
         def infer_work_mode(*a): return None
         def normalize_location(l): return {"full": l, "city": None, "state": None, "country": None}
         def infer_seniority(*a): return None 
         def infer_department(*a): return None
         def bucket_posted(*a): return None
         def extract_salary(*a): return None, None, None
         def infer_visa(*a): return None, None
         def extract_all_enrichment(*a): return {}

    processed_jobs = []
    enrichment_data = []

    for job in jobs:
        title = job.get("title", "")
        desc = job.get("job_description", "")
        
        # Calculate derived fields
        loc_raw = job.get("location", "")
        try:
            loc_data = normalize_location(loc_raw)
        except:
             loc_data = {"full": loc_raw, "city": None, "state": None, "country": None}
        
        try:
            work_mode = infer_work_mode(loc_raw, desc)
            is_remote = True if work_mode in ["remote", "hybrid"] else False
            seniority = infer_seniority(title, desc)
            department = infer_department(title, desc)
            posted_bucket = bucket_posted(job.get("date_posted"))
            salary_min, salary_max, salary_curr = extract_salary(desc)
            visa_sponsorship, visa_conf = infer_visa(desc)
        except:
            # Fallback if intelligence fails
            work_mode, is_remote, seniority, department, posted_bucket = None, False, None, None, None
            salary_min, salary_max, salary_curr, visa_sponsorship, visa_conf = None, None, None, None, None

        # Location Normalization (Ontology matching)
        matcher = get_matcher(DATABASE_URL)
        location_id = matcher.match(loc_raw)

        # Calculate description hash for deduplication
        desc_hash = hashlib.md5(desc.encode('utf-8')).hexdigest() if desc else None

        processed_jobs.append((
            job.get("job_id"),
            title,
            job.get("company"),
            loc_raw, # location
            desc,
            job.get("job_link"),
            job.get("source"),
            job.get("date_posted"), # Should be handled by adapter if string
            is_remote,
            work_mode,
            seniority,
            department,
            posted_bucket,
            today_str, # ingested_at
            salary_min, salary_max, salary_curr,
            visa_sponsorship, visa_conf,
            loc_data.get("full"), loc_data.get("city"), loc_data.get("state"), loc_data.get("country"),
            desc_hash,
            location_id
        ))
        
        # Enrichment Data - DEPRECATED in Scraper (Moved to Async Worker)
        # try:
        #     enrichment = extract_all_enrichment(desc)
        # except:
        #     enrichment = {}
            
        # enrichment_data.append((...))

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Insert Jobs
            execute_batch(cur, """
                INSERT INTO jobs (
                    job_id, title, company, location, job_description, job_link, source, date_posted,
                    is_remote, work_mode, seniority, department, posted_bucket, ingested_at,
                    salary_min, salary_max, salary_currency, visa_sponsorship, visa_confidence,
                    normalized_location, city, state, country, enrichment_status, description_hash,
                    location_id
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, 'pending', %s, %s
                ) ON CONFLICT (job_id) DO NOTHING;
            """, processed_jobs)

            # 2. Insert Enrichment - MOVED TO WORKER
            # execute_batch(cur, """
            #     INSERT INTO job_enrichment ...
            # """, enrichment_data)
            
            # 3. Sync to Search Projection Layer (JOB_SEARCH)
            # Must happen after jobs/enrichment are committed so we can SELECT from them.
    
    # Extract IDs to sync
    job_ids = [j[0] for j in processed_jobs]
    if job_ids:
        upsert_job_search_projection(job_ids)

    return len(jobs)


def upsert_job_search_projection(job_ids):
    """
    Syncs the given job IDs to the JOB_SEARCH denormalized table.
    """
    if not job_ids: return

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Upsert Data using CTE for clarity and JOIN deduplication
            cur.execute("""
                WITH job_data AS (
                    SELECT DISTINCT ON (j.job_id)
                        j.job_id,
                        j.company as company_id,
                        j.title,
                        j.location,
                        j.work_mode,
                        je.experience_min,
                        je.experience_max,
                        TRIM(CONCAT_WS(' ', je.tech_languages, je.tech_frameworks, je.tech_cloud, je.tech_tools, je.tech_data)) as tech_stack_text,
                        je.job_summary,
                        j.date_posted,
                        TRUE as is_active,
                        j.normalized_location,
                        j.job_link,
                        j.ingested_at,
                        je.employment_type,
                        ARRAY_REMOVE(ARRAY[je.tech_languages, je.tech_frameworks, je.tech_cloud, je.tech_tools, je.tech_data], NULL) as skills,
                        c.logo_url,
                        j.salary_min,
                        j.salary_max,
                        j.salary_currency,
                        j.visa_sponsorship,
                        j.location_id,
                        je.skill_ids
                    FROM jobs j
                    LEFT JOIN job_enrichment je ON j.job_id = je.job_id
                    LEFT JOIN companies c ON j.company = c.name
                    WHERE j.job_id = ANY(%s)
                    ORDER BY j.job_id, je.enriched_at DESC NULLS LAST
                )
                INSERT INTO job_search (
                    job_id, company_id, title, location, work_mode,
                    experience_min, experience_max, tech_stack_text, job_summary,
                    date_posted, is_active, normalized_location, job_link,
                    ingested_at, employment_type, skills, logo_url,
                    salary_min, salary_max, salary_currency, visa_sponsorship,
                    location_id, skill_ids
                )
                SELECT * FROM job_data
                ON CONFLICT (job_id) DO UPDATE SET
                    company_id = EXCLUDED.company_id,
                    title = EXCLUDED.title,
                    location = EXCLUDED.location,
                    work_mode = EXCLUDED.work_mode,
                    experience_min = EXCLUDED.experience_min,
                    experience_max = EXCLUDED.experience_max,
                    tech_stack_text = EXCLUDED.tech_stack_text,
                    job_summary = EXCLUDED.job_summary,
                    date_posted = EXCLUDED.date_posted,
                    is_active = EXCLUDED.is_active,
                    normalized_location = EXCLUDED.normalized_location,
                    job_link = EXCLUDED.job_link,
                    ingested_at = EXCLUDED.ingested_at,
                    employment_type = EXCLUDED.employment_type,
                    skills = EXCLUDED.skills,
                    logo_url = EXCLUDED.logo_url,
                    salary_min = EXCLUDED.salary_min,
                    salary_max = EXCLUDED.salary_max,
                    salary_currency = EXCLUDED.salary_currency,
                    visa_sponsorship = EXCLUDED.visa_sponsorship,
                    location_id = EXCLUDED.location_id,
                    skill_ids = EXCLUDED.skill_ids;
            """, (job_ids,))
            
            # Update Vector (Separately to apply weights)
            cur.execute("""
                UPDATE job_search
                SET search_vector =
                    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                    setweight(to_tsvector('english', coalesce(tech_stack_text, '')), 'A') ||
                    setweight(to_tsvector('english', coalesce(job_summary, '')), 'B') ||
                    setweight(to_tsvector('english', coalesce(location, '')), 'C') ||
                    setweight(to_tsvector('english', coalesce(normalized_location, '')), 'C')
                WHERE job_id = ANY(%s);
            """, (job_ids,))

def save_raw_job(job_id, source, raw_data_dict):
    """
    Saves raw API response.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO raw_jobs (job_id, source, raw_payload, fetched_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (job_id) DO UPDATE SET
                    raw_payload = EXCLUDED.raw_payload,
                    fetched_at = NOW();
            """, (job_id, source, json.dumps(raw_data_dict)))

# -------- COMPANY MANAGEMENT --------

def add_company(name, ats_url, ats_provider, career_page_url=None, domain=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO companies (name, ats_url, ats_provider, career_page_url, domain)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (ats_url) DO NOTHING
                RETURNING id;
            """, (name, ats_url, ats_provider, career_page_url, domain))
            return cur.fetchone() is not None

def get_active_companies():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM companies 
                WHERE active = TRUE 
                  AND (circuit_open_until IS NULL OR circuit_open_until <= NOW())
            """)
            return cur.fetchall()

def update_last_scraped(company_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE companies SET last_scraped_at = NOW() WHERE id = %s", (company_id,))

# -------- CIRCUIT BREAKER --------

def record_company_failure(company_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Atomic update using specific Postgres features is better, but stick to logic
            cur.execute("SELECT consecutive_failures FROM companies WHERE id = %s", (company_id,))
            row = cur.fetchone()
            if row:
                fails = (row[0] or 0) + 1
                if fails >= 3:
                     # Open circuit for 7 days
                     cur.execute("""
                        UPDATE companies SET 
                            consecutive_failures = %s,
                            last_failure_at = NOW(),
                            circuit_open_until = NOW() + INTERVAL '7 days'
                        WHERE id = %s
                     """, (fails, company_id))
                else:
                     cur.execute("""
                        UPDATE companies SET 
                            consecutive_failures = %s,
                            last_failure_at = NOW()
                        WHERE id = %s
                     """, (fails, company_id))

def record_company_success(company_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE companies SET 
                    consecutive_failures = 0,
                    last_success_at = NOW(),
                    circuit_open_until = NULL
                WHERE id = %s
            """, (company_id,))

def get_companies_with_open_circuits():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, ats_provider, consecutive_failures, last_failure_at, circuit_open_until
                FROM companies
                WHERE circuit_open_until > NOW()
            """)
            return cur.fetchall()

def record_endpoint_result(endpoint_id, success, jobs_found=0, error_msg=None):

    """
    Updates career_endpoints with the result of a scrape.
    """
    if not endpoint_id: return

    with get_connection() as conn:
        with conn.cursor() as cur:
            if success:
                cur.execute("""
                    UPDATE career_endpoints SET 
                        last_ingested_at = NOW(),
                        consecutive_failures = 0,
                        last_failure_reason = NULL,
                        verification_status = 'verified' -- Successful scrape implies verification
                    WHERE id = %s
                """, (endpoint_id,))
            else:
                cur.execute("""
                    UPDATE career_endpoints SET 
                        consecutive_failures = consecutive_failures + 1,
                        last_failure_reason = %s
                    WHERE id = %s
                """, (error_msg, endpoint_id))


# -------- FINGERPRINTS --------

def save_workday_fingerprint(company_slug, career_url, endpoint_url, method, headers, payload):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO workday_fingerprints 
                (company_slug, career_url, endpoint_url, method, headers, payload_template, status, verified_at)
                VALUES (%s, %s, %s, %s, %s, %s, 'active', NOW())
                ON CONFLICT (company_slug) DO UPDATE SET
                    endpoint_url = EXCLUDED.endpoint_url,
                    headers = EXCLUDED.headers,
                    payload_template = EXCLUDED.payload_template,
                    verified_at = NOW();
            """, (company_slug, career_url, endpoint_url, method, json.dumps(headers), json.dumps(payload)))

def get_workday_fingerprint(company_slug):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM workday_fingerprints 
                WHERE company_slug = %s AND status = 'active'
            """, (company_slug,))
            row = cur.fetchone()
            # Postgres JSONB comes back as dict automatically with psycopg2 extras, usually.
            # But just in case
            return row

# -------- HELPERS --------

def get_all_jobs():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM jobs")
            return cur.fetchall()

def update_job_fields(job_id, fields_dict):
    if not fields_dict: return
    
    cols = list(fields_dict.keys())
    vals = list(fields_dict.values())
    vals.append(job_id)
    
    set_clause = ", ".join([f"{col} = %s" for col in cols])
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE jobs SET {set_clause} WHERE job_id = %s", vals)

# -------- ENRICHMENT WORKER SUPPORT --------

def get_unenriched_jobs(limit=50):
    """
    Fetches job_id and specific text fields for enrichment.
    Uses the optimized enrichment_status index.
    """
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT j.job_id, j.job_description, j.title, j.location, j.date_posted, j.description_hash, j.retry_count
                FROM jobs j
                WHERE (j.enrichment_status = 'pending'
                   OR j.enrichment_status IS NULL
                   OR j.enrichment_status = 'stale'
                   OR (j.enrichment_status = 'failed' AND j.retry_count < 3))
                ORDER BY j.date_posted DESC
                LIMIT %s
            """, (limit,))
            return cur.fetchall()

def update_job_status(job_id, status):
    """Updates the enrichment status of a job."""
    valid_statuses = ['pending', 'processing', 'completed', 'failed', 'stale']
    if status not in valid_statuses:
        return
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE jobs SET enrichment_status = %s WHERE job_id = %s", (status, job_id))

def fail_job(job_id):
    """Marks a job as failed and increments its retry count."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE jobs 
                SET enrichment_status = 'failed',
                    retry_count = COALESCE(retry_count, 0) + 1
                WHERE job_id = %s
            """, (job_id,))

def get_enrichment_by_hash(desc_hash):
    """
    Finds existing enrichment data for a given description hash.
    Used for shared intelligence (recycling LLM results).
    """
    if not desc_hash: return None
    
    with get_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT enr.* 
                FROM job_enrichment enr
                JOIN jobs j ON enr.job_id = j.job_id
                WHERE j.description_hash = %s
                LIMIT 1
            """, (desc_hash,))
            return cur.fetchone()

def save_enrichment(job_id, enrichment_data):
    """
    Saves extracted intelligence to job_enrichment table.
    """
    if not enrichment_data: return

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Debug: Check if job exists visible to this transaction
            cur.execute("SELECT 1 FROM jobs WHERE job_id = %s", (job_id,))
            if not cur.fetchone():
                print(f"❌ CRITICAL DEBUG: Job {job_id} NOT FOUND in jobs table before insert!")
            else:
                print(f"✅ DEBUG: Job {job_id} found in jobs table.")

            cur.execute("""
                INSERT INTO job_enrichment (
                    job_id, 
                    tech_languages, tech_frameworks, tech_tools, tech_cloud, tech_data,
                    experience_years, seniority_tier, seniority_level,
                    education_level, certifications, soft_skills,
                    natural_languages, job_summary, 
                    enrichment_tier, enrichment_source,
                    employment_type,
                    embedding,
                    skill_ids, concept_ids,
                    enriched_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, 
                    %s, %s,
                    %s,
                    %s,
                    %s, %s,
                    NOW()
                )
                ON CONFLICT (job_id) DO UPDATE SET
                    tech_languages = EXCLUDED.tech_languages,
                    tech_frameworks = EXCLUDED.tech_frameworks,
                    tech_tools = EXCLUDED.tech_tools,
                    tech_cloud = EXCLUDED.tech_cloud,
                    tech_data = EXCLUDED.tech_data,
                    experience_years = EXCLUDED.experience_years,
                    seniority_tier = EXCLUDED.seniority_tier,
                    seniority_level = EXCLUDED.seniority_level,
                    education_level = EXCLUDED.education_level,
                    certifications = EXCLUDED.certifications,
                    soft_skills = EXCLUDED.soft_skills,
                    natural_languages = EXCLUDED.natural_languages,
                    job_summary = EXCLUDED.job_summary,
                    enrichment_tier = EXCLUDED.enrichment_tier,
                    enrichment_source = EXCLUDED.enrichment_source,
                    employment_type = EXCLUDED.employment_type,
                    embedding = EXCLUDED.embedding,
                    skill_ids = EXCLUDED.skill_ids,
                    concept_ids = EXCLUDED.concept_ids,
                    ontology_synced_at = NOW(),
                    enriched_at = NOW();
            """, (
                job_id,
                enrichment_data.get("tech_languages"), 
                enrichment_data.get("tech_frameworks"),
                enrichment_data.get("tech_tools"),
                enrichment_data.get("tech_cloud"),
                enrichment_data.get("tech_data"),
                enrichment_data.get("experience_years"),
                enrichment_data.get("seniority_tier"),
                enrichment_data.get("seniority_level"),
                enrichment_data.get("education_level"),
                ", ".join(enrichment_data.get("certifications") or []) if enrichment_data.get("certifications") else None,
                enrichment_data.get("soft_skills"), # Passed as list for Text[] column
                enrichment_data.get("natural_languages"),
                enrichment_data.get("job_summary"),
                enrichment_data.get("enrichment_tier", "basic"),
                enrichment_data.get("enrichment_source", "manual"),
                enrichment_data.get("employment_type"),
                enrichment_data.get("embedding"),
                enrichment_data.get("skill_ids", []),
                enrichment_data.get("concept_ids", [])
            ))
    
    # Update Search Projection immediately
    upsert_job_search_projection([job_id])
