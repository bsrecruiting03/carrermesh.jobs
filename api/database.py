"""Database connection and query functions."""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging

from .config import settings

logger = logging.getLogger(__name__)


import psycopg2.pool
import threading

# Global connection pool
db_pool = None
_pool_lock = threading.Lock()

def init_db_pool():
    """Initialize the connection pool if it doesn't exist."""
    global db_pool
    if db_pool is None:
        with _pool_lock:
            if db_pool is None:
                try:
                    db_pool = psycopg2.pool.ThreadedConnectionPool(
                        minconn=1,
                        maxconn=20,
                        dsn=settings.database_url
                    )
                    logger.info("Database connection pool initialized.")
                except psycopg2.Error as e:
                    logger.error(f"Failed to initialize connection pool: {e}")
                    raise

@contextmanager
def get_db():
    """Get database connection from pool."""
    global db_pool
    if db_pool is None:
        init_db_pool()
        
    conn = None
    try:
        conn = db_pool.getconn()
        yield conn
    except psycopg2.Error as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            db_pool.putconn(conn)


def test_connection() -> bool:
    """Test database connection."""
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False


# ============= JOB QUERIES =============

def parse_tech_stack(enrichment: Optional[Dict]) -> List[str]:
    """Parse tech stack from enrichment data."""
    if not enrichment:
        return []
    
    tech_items = []
    for field in ['tech_languages', 'tech_frameworks', 'tech_cloud', 'tech_data']:
        value = enrichment.get(field)
        if value:
            tech_items.extend([t.strip() for t in value.split(',')])
    
    return list(set(tech_items))  # Remove duplicates


def build_job_search_query(
    query: Optional[str] = None,
    location: Optional[str] = None,
    remote: Optional[bool] = None,
    department: Optional[str] = None,
    department_category: Optional[str] = None,
    department_subcategory: Optional[str] = None,
    tech_stack: Optional[str] = None,
    min_salary: Optional[int] = None,
    max_salary: Optional[int] = None,
    visa_sponsorship: Optional[str] = None,
    remote_policy: Optional[str] = None,
    seniority: Optional[str] = None,
    soft_skills: Optional[str] = None,
    posted_since: Optional[str] = None,
    sort: str = "date_posted",
    offset: int = 0,
    limit: int = 20
) -> Tuple[str, List[Any]]:
    """
    Build SQL query for job search with filters.
    Optimized: Uses a 'Recent-First' Candidate Selection strategy for text searches.
    """
    params = []
    where_clauses = []
    
    # --- 1. BUILD WHERE CLAUSES (Common for both Inner and Outer queries) ---
    
    # Search query
    if query:
        # Hybrid Search: Full Text OR Fuzzy Title Match
        where_clauses.append("(j.search_vector @@ plainto_tsquery('english', %s) OR j.title % %s)")
        params.extend([query, query])
    
    # Location
    if location:
        resolved = resolve_location(location)
        if resolved:
            location_ids = get_location_children(resolved['id'])
            if location_ids:
                placeholders = ','.join(['%s'] * len(location_ids))
                where_clauses.append(f"j.location_id IN ({placeholders})")
                params.extend(location_ids)
            else:
                where_clauses.append("j.location_id = %s")
                params.append(resolved['id'])
        else:
            # Fallback to text search for unrecognized locations
            where_clauses.append("(j.city ILIKE %s OR j.state ILIKE %s OR j.country ILIKE %s)")
            loc_pattern = f"%{location}%"
            params.extend([loc_pattern, loc_pattern, loc_pattern])
    
    if remote is not None:
        where_clauses.append("j.is_remote = %s")
        params.append(remote)
    
    if department:
        where_clauses.append("j.department ILIKE %s")
        params.append(f"%{department}%")

    if department_category:
        where_clauses.append("j.department_category = %s")
        params.append(department_category)

    if department_subcategory:
        where_clauses.append("j.department_subcategory = %s")
        params.append(department_subcategory)
    
    if tech_stack:
        tech_items = [t.strip() for t in tech_stack.split(',')]
        tech_conditions = []
        for tech in tech_items:
            tech_conditions.append(
                "(e.tech_languages ILIKE %s OR e.tech_frameworks ILIKE %s OR "
                "e.tech_cloud ILIKE %s OR e.tech_tools ILIKE %s)"
            )
            tech_pattern = f"%{tech}%"
            params.extend([tech_pattern, tech_pattern, tech_pattern, tech_pattern])
        where_clauses.append(f"({' OR '.join(tech_conditions)})")
    
    if min_salary:
        where_clauses.append("j.salary_min >= %s")
        params.append(min_salary)
    
    if max_salary:
        where_clauses.append("j.salary_max <= %s")
        params.append(max_salary)
    
    if visa_sponsorship:
        where_clauses.append("j.visa_sponsorship = %s")
        params.append(visa_sponsorship)
    
    if remote_policy:
        # remote_policy can be: 'remote', 'hybrid', 'onsite', 'unspecified'
        where_clauses.append("j.work_mode ILIKE %s")
        params.append(f"%{remote_policy}%")
    
    if seniority:
        # Match against enrichment seniority data if available
        where_clauses.append("(e.seniority ILIKE %s OR j.seniority ILIKE %s)")
        params.extend([f"%{seniority}%", f"%{seniority}%"])
    
    if soft_skills:
        skills_list = [s.strip() for s in soft_skills.split(',')]
        # Use simple ILIKE for standard jobs table query since it joins enrichment
        # But wait, soft_skills is in job_search? Yes. But here we are building generic WHERE.
        # Check migration: Added to job_enrichment and job_search.
        # Generic query joins job_enrichment e.
        # e.soft_skills is TEXT[].
        where_clauses.append("e.soft_skills && %s")
        params.append(skills_list)
    
    if posted_since:
        days = int(posted_since.rstrip('d'))
        cutoff_date = datetime.now() - timedelta(days=days)
        where_clauses.append("j.date_posted >= %s")
        params.append(cutoff_date)

    where_str = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    # --- 2. CONSTRUCT QUERY ---
    
    # OPTIMIZATION: If 'query' is present, use the Search Projection Layer (job_search table)
    # This avoids joins during the ranking phase.
    
    
    if query:
        # Strict implementation of User's Search Contract with Candidate Filtering
        # 1. Candidate Selection using Denormalized Index (No Joins)
        #    - Apply text search
        #    - Apply filters present in job_search (location, work_mode)
        # 2. Final Projection
        #    - Join generically
        #    - Apply remaining filters (salary, dept, etc.)
        
        cte_where = ["is_active = TRUE", "search_vector @@ plainto_tsquery('english', %s)"]
        cte_params = [query]
        
        outer_where = []
        outer_params = []
        
        # --- Split Filters ---
        
        # Location (In CTE) - Use ontology for precise matching
        if location:
            resolved = resolve_location(location)
            logger.info(f"[LOCATION_DEBUG] Input: '{location}', Resolved: {resolved}")
            if resolved:
                location_ids = get_location_children(resolved['id'])
                logger.info(f"[LOCATION_DEBUG] Children IDs: {location_ids}")
                if location_ids:
                    placeholders = ','.join(['%s'] * len(location_ids))
                    cte_where.append(f"location_id IN ({placeholders})")
                    cte_params.extend(location_ids)
                else:
                    cte_where.append("location_id = %s")
                    cte_params.append(resolved['id'])
            else:
                # Fallback to text search for unrecognized locations
                cte_where.append("location ILIKE %s")
                cte_params.append(f"%{location}%")
            
        # Remote (In CTE)
        if remote is not None:
            if remote:
                cte_where.append("work_mode IN ('remote', 'hybrid')")
            else:
                cte_where.append("work_mode NOT IN ('remote')")
        
        # Department (Outer)
        if department:
            outer_where.append("j.department ILIKE %s")
            outer_params.append(f"%{department}%")

        if department_category:
            outer_where.append("j.department_category = %s")
            outer_params.append(department_category)

        if department_subcategory:
            outer_where.append("j.department_subcategory = %s")
            outer_params.append(department_subcategory)
            
        # Tech Stack (Outer - could be Inner if using text search, but stick to strict field)
        if tech_stack:
             # Already handled in generic where_clauses logic? 
             # No, we need to rebuild logic here or reuse.
             # Reusing generic logic is hard because we are splitting.
             tech_items = [t.strip() for t in tech_stack.split(',')]
             tech_conditions = []
             for tech in tech_items:
                tech_conditions.append(
                    "(e.tech_languages ILIKE %s OR e.tech_frameworks ILIKE %s OR "
                    "e.tech_cloud ILIKE %s OR e.tech_tools ILIKE %s)"
                )
                tech_pattern = f"%{tech}%"
                outer_params.extend([tech_pattern, tech_pattern, tech_pattern, tech_pattern])
             outer_where.append(f"({' OR '.join(tech_conditions)})")

        if min_salary:
            outer_where.append("j.salary_min >= %s")
            outer_params.append(min_salary)
        
        if visa_sponsorship:
            outer_where.append("j.visa_sponsorship = %s")
            outer_params.append(visa_sponsorship)

        if soft_skills:
            # For Job Search optimization (CTE), we can filter soft_skills (TEXT[])
            skills_list = [s.strip() for s in soft_skills.split(',')]
            # soft_skills is in job_search? Yes.
            # So filter in CTE?
            # CTE selects from job_search.
            # Explicitly cast to text[] just in case
            cte_where.append("soft_skills && %s") 
            cte_params.append(skills_list)
            
        if posted_since:
            days = int(posted_since.rstrip('d'))
            cutoff_date = datetime.now() - timedelta(days=days)
            # Date posted is in job_search too, so we COULD filter in CTE. Useful optimization.
            cte_where.append("date_posted >= %s")
            cte_params.append(cutoff_date)

        # Construct CTE SQL
        cte_sql_where = " AND ".join(cte_where)
        
        # Construct Outer SQL
        outer_sql_where = ("WHERE " + " AND ".join(outer_where)) if outer_where else ""

        sql = f"""
        WITH candidates AS (
            SELECT job_id, search_vector
            FROM job_search
            WHERE {cte_sql_where}
            LIMIT 1000
        ),
        ranked AS (
            SELECT 
                c.job_id,
                ts_rank(c.search_vector, plainto_tsquery('english', %s)) as rank,
                js.date_posted,
                js.skills,
                js.job_summary,
                js.skill_ids
            FROM candidates c
            JOIN job_search js ON c.job_id = js.job_id
            ORDER BY rank DESC, js.date_posted DESC
            LIMIT %s OFFSET %s
        )
        SELECT 
            j.job_id, j.title, j.company, j.location, j.is_remote, j.work_mode,
            j.department, j.department_category, j.department_subcategory,
            j.seniority, j.date_posted, j.salary_min, j.salary_max,
            j.salary_currency, j.visa_sponsorship, j.visa_confidence, j.job_link, j.source,
            -- Tech stack is now a single string in job_search, need to parse or return as is
            -- But API expects tech_languages etc.
            -- For now, let's keep it simple: The new logic parses 'tech_stack' string in python
            r.skills as tech_stack,
            r.skill_ids,
            r.job_summary,
            r.rank
        FROM ranked r
        JOIN jobs j ON r.job_id = j.job_id
        {outer_sql_where}
        ORDER BY r.rank DESC, r.date_posted DESC
        """
        
        # Param Structure:
        # 1. CTE Params (Query, Location, Remote, Date)
        # 2. Ranking Params (Query)
        # 3. Limit/Offset
        # 4. Outer Params (Dept, Salary, etc.) -> Wait, Outer Params are injected into string?
        #    NO! We must use placeholders.
        #    So "JOIN jobs j ... WHERE {outer_sql_where}"
        #    The placeholders in outer_sql_where are %s.
        #    We need to pass them in order.
        #    Wait, standard psycopg2 interpolation order:
        #    CTE params -> Rank params -> Limit/Offset -> Outer params.
        #    BUT Outer Where is physically AFTER Limit/Offset in SQL string (SELECT ... FROM ranked ... LIMIT ... -> No, Limit is inside ranked CTE).
        #    The Limit in outer query? No, Limit is in ranked CTE.
        #    The Outer Query does NOT have Limit/Offset (it selects all from ranked).
        #    So order: CTE Params -> Ranking Params -> Limit -> Offset -> Outer Params.
        
        full_params = cte_params + [query, limit, offset] + outer_params
        return sql, full_params
        
    else:
        # Standard Browse Query (No Text Search)
        # Or if sorting by Salary/Company
        
        sql = """
            SELECT 
                j.job_id, j.title, j.company, j.location, j.is_remote, j.work_mode,
                j.department, j.department_category, j.department_subcategory,
                j.seniority, j.date_posted, j.salary_min, j.salary_max,
                j.salary_currency, j.visa_sponsorship, j.visa_confidence, j.job_link, j.source,
                e.tech_languages, e.tech_frameworks, e.tech_cloud, e.tech_tools,
                e.job_summary, e.experience_years
        """
        
        if query:
             sql += """, 
                ts_rank(j.search_vector, plainto_tsquery('english', %s)) as rank,
                similarity(j.title, %s) as title_sim
            """
             # For standard query, we add rank params before WHERE params? 
             # No, SELECT list params come First.
             # but 'params' list currently has WHERE params.
             # We need to prepend rank params.
             params = [query, query] + params
        
        sql += """
            FROM jobs j
            LEFT JOIN job_enrichment e ON j.job_id = e.job_id
        """
        
        sql += where_str
        
        # Sort logic
        order_clause = "j.date_posted DESC NULLS LAST, j.job_id ASC"
        
        if sort == 'title':
            order_clause = "j.title ASC, j.job_id ASC"
        elif sort == 'company':
            order_clause = "j.company ASC, j.job_id ASC"
        elif sort == 'salary':
            order_clause = "j.salary_max DESC NULLS LAST, j.job_id ASC"
        elif query:
             # Fallback if we decided NOT to use optimized path (e.g. user selected 'sort by salary' but typed a query)
             order_clause = "(rank + title_sim) DESC, j.date_posted DESC NULLS LAST"

        sql += f" ORDER BY {order_clause}"
        sql += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        return sql, params


def count_jobs_query(
    query: Optional[str] = None,
    location: Optional[str] = None,
    remote: Optional[bool] = None,
    department: Optional[str] = None,
    department_category: Optional[str] = None,
    department_subcategory: Optional[str] = None,
    tech_stack: Optional[str] = None,
    min_salary: Optional[int] = None,
    visa_sponsorship: Optional[str] = None,
    soft_skills: Optional[str] = None,
    posted_since: Optional[str] = None
) -> Tuple[str, List[Any]]:
    """Build count query for total results."""
    params = []
    where_clauses = []
    
    MAX_COUNT_LIMIT = 5000 
    
    if query:
        # Optimized Count on JOB_SEARCH
        sql = "SELECT COUNT(*) FROM job_search j"
        where_clauses.append("j.is_active = TRUE")
        where_clauses.append("j.search_vector @@ plainto_tsquery('english', %s)")
        params.append(query)
        
        # Apply filters valid for job_search
        if location:
            where_clauses.append("j.location ILIKE %s")
            params.append(f"%{location}%")
        
        if remote is not None:
             # job_search has 'work_mode' string, not boolean
             if remote:
                 where_clauses.append("j.work_mode IN ('remote', 'hybrid')")
             else:
                 where_clauses.append("j.work_mode NOT IN ('remote')")
                 
        # Note: Department/Salary filters are not fully optimized on job_search yet.
        # We skip them for count approximation to avoid joins, or we could add them to schema later.
        
    else:
        # Standard Browse -> Use JOBS table
        sql = """
            SELECT COUNT(DISTINCT j.job_id)
            FROM jobs j
            LEFT JOIN job_enrichment e ON j.job_id = e.job_id
        """
        
        # Apply full filters for standard browse
        if location:
            # Try to resolve location using ontology first
            resolved = resolve_location(location)
            if resolved:
                # Use location_id for precise matching
                location_ids = get_location_children(resolved['id'])
                if location_ids:
                    placeholders = ','.join(['%s'] * len(location_ids))
                    where_clauses.append(f"j.location_id IN ({placeholders})")
                    params.extend(location_ids)
                else:
                    where_clauses.append("j.location_id = %s")
                    params.append(resolved['id'])
            else:
                # Fallback to text search for unrecognized locations
                where_clauses.append("(j.location ILIKE %s OR j.city ILIKE %s OR j.state ILIKE %s OR j.country ILIKE %s)")
                loc_pattern = f"%{location}%"
                params.extend([loc_pattern, loc_pattern, loc_pattern, loc_pattern])
        
        if remote is not None:
            where_clauses.append("j.is_remote = %s")
            params.append(remote)
            
        if department:
            where_clauses.append("j.department ILIKE %s")
            params.append(f"%{department}%")

        if department_category:
            where_clauses.append("j.department_category = %s")
            params.append(department_category)

        if department_subcategory:
            where_clauses.append("j.department_subcategory = %s")
            params.append(department_subcategory)
        
        if tech_stack:
            tech_items = [t.strip() for t in tech_stack.split(',')]
            tech_conditions = []
            for tech in tech_items:
                tech_conditions.append(
                    "(e.tech_languages ILIKE %s OR e.tech_frameworks ILIKE %s OR "
                    "e.tech_cloud ILIKE %s OR e.tech_tools ILIKE %s)"
                )
                tech_pattern = f"%{tech}%"
                params.extend([tech_pattern, tech_pattern, tech_pattern, tech_pattern])
            
            where_clauses.append(f"({' OR '.join(tech_conditions)})")
        
        if min_salary:
            where_clauses.append("j.salary_min >= %s")
            params.append(min_salary)
        
        if visa_sponsorship:
            where_clauses.append("j.visa_sponsorship = %s")
            params.append(visa_sponsorship)

        if soft_skills:
            skills_list = [s.strip() for s in soft_skills.split(',')]
            where_clauses.append("e.soft_skills && %s")
            params.append(skills_list)
        
        if posted_since:
            days = int(posted_since.rstrip('d'))
            cutoff_date = datetime.now() - timedelta(days=days)
            where_clauses.append("j.date_posted >= %s")
            params.append(cutoff_date)
    
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    
    return sql, params


def search_jobs(
    query: Optional[str] = None,
    location: Optional[str] = None,
    remote: Optional[bool] = None,
    department: Optional[str] = None,
    department_category: Optional[str] = None,
    department_subcategory: Optional[str] = None,
    tech_stack: Optional[str] = None,
    min_salary: Optional[int] = None,
    visa_sponsorship: Optional[str] = None,
    soft_skills: Optional[str] = None,
    posted_since: Optional[str] = None,
    sort: str = "date_posted",
    page: int = 1,
    limit: int = 20
) -> Tuple[List[Dict], int]:
    """
    Search jobs with filters and pagination.
    Returns (jobs_list, total_count)
    """
    offset = (page - 1) * limit
    
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Set fuzzy threshold to 0.3 (allows for meaningful typos but reduces noise)
        cur.execute("SELECT set_limit(0.3)")
        
        # Get total count
        count_sql, count_params = count_jobs_query(
            query=query, location=location, remote=remote, department=department, 
            department_category=department_category, department_subcategory=department_subcategory,
            tech_stack=tech_stack, min_salary=min_salary, visa_sponsorship=visa_sponsorship, 
            soft_skills=soft_skills, posted_since=posted_since
        )
        cur.execute(count_sql, count_params)
        total = cur.fetchone()['count']
        
        # Get jobs
        import time
        start_time = time.perf_counter()
        
        search_sql, search_params = build_job_search_query(
            query=query, location=location, remote=remote, department=department, 
            department_category=department_category, department_subcategory=department_subcategory,
            tech_stack=tech_stack, min_salary=min_salary, visa_sponsorship=visa_sponsorship, 
            soft_skills=soft_skills, posted_since=posted_since,
            sort=sort, offset=offset, limit=limit
        )
        cur.execute(search_sql, search_params)
        jobs = cur.fetchall()
        
        execution_time = (time.perf_counter() - start_time) * 1000
        logger.info(f"[SEARCH_LATENCY] Query='{query}' Rows={len(jobs)} Time={execution_time:.2f}ms")
        
        # Parse tech stack for each job
        for job in jobs:
            if job.get('tech_stack'):
                # Optimized path: Use the skills list from job_search
                pass 
            else:
                # Fallback / Standard Browse path
                enrichment = {
                    'tech_languages': job.get('tech_languages'),
                    'tech_frameworks': job.get('tech_frameworks'),
                    'tech_cloud': job.get('tech_cloud'),
                    'tech_tools': job.get('tech_tools')
                }
                job['tech_stack'] = parse_tech_stack(enrichment)
        
        return [dict(job) for job in jobs], total


def get_job_by_id(job_id: str) -> Optional[Dict]:
    """Get full job details by ID."""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        sql = """
            SELECT 
                j.job_id, j.title, j.company, j.location, j.normalized_location, j.city, j.state, j.country,
                j.is_remote, j.work_mode, j.seniority, j.department, j.department_category, j.department_subcategory,
                j.salary_min, j.salary_max, j.salary_currency, j.visa_sponsorship,
                j.date_posted, j.job_link, j.source, j.job_description,
                e.tech_languages, e.tech_frameworks, e.tech_cloud, e.tech_tools,
                e.experience_years, 
                e.education_level, e.seniority_tier, e.seniority_level, 
                e.certifications, e.soft_skills,
                e.skill_ids, e.concept_ids,
                e.job_summary,
                c.name as company_name, c.domain as company_domain,
                c.ats_provider as company_ats_provider
            FROM jobs j
            LEFT JOIN job_enrichment e ON j.job_id = e.job_id
            LEFT JOIN companies c ON j.company = c.name
            WHERE j.job_id = %s
        """
        
        cur.execute(sql, (job_id,))
        job = cur.fetchone()
        
        if not job:
            return None
        
        # Structure the response
        result = dict(job)
        
        # Add enrichment object
        # check if any enrichment exists (using a few key fields)
        if any([job.get('tech_languages'), job.get('seniority_tier'), job.get('certifications')]):
            result['enrichment'] = {
                'tech_languages': job.get('tech_languages'),
                'tech_frameworks': job.get('tech_frameworks'),
                'tech_cloud': job.get('tech_cloud'),
                'tech_data': job.get('tech_data'),
                'tech_tools': job.get('tech_tools'),
                'experience_years': job.get('experience_years'),
                'education_level': job.get('education_level'),
                'seniority_tier': job.get('seniority_tier'),
                'seniority_level': job.get('seniority_level'),
                'certifications': job.get('certifications'),
                'soft_skills': job.get('soft_skills'),
                'skill_ids': job.get('skill_ids'),
                'concept_ids': job.get('concept_ids'),
                'job_summary': job.get('job_summary')
            }
        
        # Add company details
        if job.get('company_name'):
            result['company_details'] = {
                'name': job.get('company_name'),
                'domain': job.get('company_domain'),
                'ats_provider': job.get('company_ats_provider')
            }
        
        return result


# ============= COMPANY QUERIES =============

def get_companies(
    ats_provider: Optional[str] = None,
    active: bool = True,
    page: int = 1,
    limit: int = 20
) -> Tuple[List[Dict], int]:
    """Get companies with filters and pagination."""
    offset = (page - 1) * limit
    params = []
    where_clauses = []
    
    # Count query
    count_sql = "SELECT COUNT(*) FROM companies"
    
    # Active filter
    if active:
        where_clauses.append("active = %s")
        params.append(active)
    
    # ATS provider filter
    if ats_provider:
        where_clauses.append("ats_provider = %s")
        params.append(ats_provider)
    
    if where_clauses:
        count_sql += " WHERE " + " AND ".join(where_clauses)
    
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get total count
        cur.execute(count_sql, params)
        total = cur.fetchone()['count']
        
        # Get companies with job count
        list_sql = """
            SELECT 
                c.id, c.name, c.domain, c.ats_provider, c.last_scraped_at,
                COUNT(j.job_id) as active_jobs_count
            FROM companies c
            LEFT JOIN jobs j ON c.name = j.company
        """
        
        if where_clauses:
            list_sql += " WHERE " + " AND ".join(where_clauses)
        
        list_sql += """
            GROUP BY c.id, c.name, c.domain, c.ats_provider, c.last_scraped_at
            ORDER BY active_jobs_count DESC
            LIMIT %s OFFSET %s
        """
        
        params.extend([limit, offset])
        cur.execute(list_sql, params)
        companies = cur.fetchall()
        
        return [dict(c) for c in companies], total


def get_company_by_id(company_id: int) -> Optional[Dict]:
    """Get company details by ID."""
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get company details
        company_sql = """
            SELECT id, name, domain, career_page_url, ats_provider, active
            FROM companies
            WHERE id = %s
        """
        cur.execute(company_sql, (company_id,))
        company = cur.fetchone()
        
        if not company:
            return None
        
        result = dict(company)
        
        # Get job count
        cur.execute("SELECT COUNT(*) FROM jobs WHERE company = %s", (company['name'],))
        result['job_count'] = cur.fetchone()['count']
        
        # Get recent jobs (last 10)
        jobs_sql = """
            SELECT 
                job_id, title, location, is_remote, department, 
                date_posted, salary_min, salary_max, job_link, source
            FROM jobs
            WHERE company = %s
            ORDER BY date_posted DESC
            LIMIT 10
        """
        cur.execute(jobs_sql, (company['name'],))
        jobs = cur.fetchall()
        result['recent_jobs'] = [dict(j) for j in jobs]
        
        return result


# ============= FILTER QUERIES =============

def get_filter_options() -> Dict[str, List[str]]:
    """Get all available filter options (distinct values)."""
    with get_db() as conn:
        cur = conn.cursor()
        
        filters = {}
        
        # Locations (top 100)
        cur.execute("""
            SELECT DISTINCT normalized_location 
            FROM jobs 
            WHERE normalized_location IS NOT NULL
            ORDER BY normalized_location
            LIMIT 100
        """)
        filters['locations'] = [row[0] for row in cur.fetchall()]
        
        # Departments (Hierarchical)
        # We want to return the full taxonomy structure found in DB
        cur.execute("""
            SELECT DISTINCT department_category, department_subcategory 
            FROM jobs 
            WHERE department_category IS NOT NULL
        """)
        
        # Build nested structure
        dept_tree = {}
        for cat, sub in cur.fetchall():
            if cat not in dept_tree:
                dept_tree[cat] = set()
            if sub and sub != 'Uncategorized':
                dept_tree[cat].add(sub)
        
        # Convert sets to sorted lists
        filters['departments'] = {k: sorted(list(v)) for k, v in dept_tree.items()} 
        
        # Tech languages (parse from enrichment)
        cur.execute("""
            SELECT DISTINCT tech_languages
            FROM job_enrichment
            WHERE tech_languages IS NOT NULL
            LIMIT 200
        """)
        languages = set()
        for row in cur.fetchall():
            if row[0]:
                languages.update([lang.strip() for lang in row[0].split(',')])
        filters['tech_languages'] = sorted(list(languages))[:50]
        
        # Tech frameworks
        cur.execute("""
            SELECT DISTINCT tech_frameworks
            FROM job_enrichment
            WHERE tech_frameworks IS NOT NULL
            LIMIT 200
        """)
        frameworks = set()
        for row in cur.fetchall():
            if row[0]:
                frameworks.update([fw.strip() for fw in row[0].split(',')])
        filters['tech_frameworks'] = sorted(list(frameworks))[:50]
        
        # ATS providers
        cur.execute("""
            SELECT DISTINCT ats_provider 
            FROM companies 
            WHERE ats_provider IS NOT NULL
            ORDER BY ats_provider
        """)
        filters['ats_providers'] = [row[0] for row in cur.fetchall()]
        
        # Seniority levels
        cur.execute("""
            SELECT DISTINCT seniority 
            FROM jobs 
            WHERE seniority IS NOT NULL
            ORDER BY seniority
        """)
        filters['seniority_levels'] = [row[0] for row in cur.fetchall()]
        
        # Work modes
        cur.execute("""
            SELECT DISTINCT work_mode 
            FROM jobs 
            WHERE work_mode IS NOT NULL
            ORDER BY work_mode
        """)
        filters['work_modes'] = [row[0] for row in cur.fetchall()]
        
        return filters


def get_location_suggestions(prefix: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get location suggestions based on prefix using the ontology.
    Resolves aliases to canonical locations (USA = United States = America).
    Returns: [{id: int, name: str, type: str, count: int}]
    """
    if not prefix or len(prefix) < 2:
        return []
        
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Search aliases, return canonical location with job count
        sql = """
            SELECT DISTINCT ON (l.id)
                l.id,
                l.name,
                l.type,
                COALESCE(l.job_count, 0) as count,
                la.priority
            FROM location_aliases la
            JOIN locations l ON la.location_id = l.id
            WHERE la.alias ILIKE %s
            ORDER BY l.id, la.priority DESC
        """
        
        search_pattern = f"{prefix}%"
        cur.execute(sql, (search_pattern,))
        alias_matches = cur.fetchall()
        
        # Also search location names directly
        cur.execute("""
            SELECT 
                l.id,
                l.name,
                l.type,
                COALESCE(l.job_count, 0) as count,
                10 as priority
            FROM locations l
            WHERE l.name ILIKE %s
            AND l.id NOT IN (SELECT location_id FROM location_aliases WHERE alias ILIKE %s)
        """, (search_pattern, search_pattern))
        name_matches = cur.fetchall()
        
        # Combine and sort
        all_matches = list(alias_matches) + list(name_matches)
        
        # Sort by type priority (country first) then by count
        type_priority = {'country': 1, 'state': 2, 'city': 3}
        all_matches.sort(key=lambda x: (type_priority.get(x['type'], 9), -x['count']))
        
        results = []
        seen_ids = set()
        for row in all_matches[:limit]:
            if row['id'] not in seen_ids:
                seen_ids.add(row['id'])
                results.append({
                    'id': row['id'],
                    'name': row['name'],
                    'type': row['type'],
                    'count': row['count']
                })
        
        return results


def get_job_suggestions(prefix: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get job suggestions (titles, companies) based on prefix.
    Returns list of {text: str, type: str, count: int}
    """
    if not prefix or len(prefix) < 2:
        return []
        
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Search Titles and Companies
        # We group by text to avoid duplicates
        sql = """
            WITH title_matches AS (
                SELECT 
                    title as text, 
                    'role' as type,
                    COUNT(*) as count
                FROM jobs 
                WHERE title ILIKE %s
                GROUP BY title
            ),
            company_matches AS (
                SELECT 
                    c.name as text, 
                    'company' as type,
                    COUNT(j.id) as count
                FROM companies c
                JOIN jobs j ON j.company_id = c.id
                WHERE c.name ILIKE %s
                GROUP BY c.name
            )
            SELECT * FROM title_matches
            UNION ALL
            SELECT * FROM company_matches
            ORDER BY count DESC
            LIMIT %s
        """
        
        search_pattern = f"%{prefix}%" # ILIKE pattern
        cur.execute(sql, (search_pattern, search_pattern, limit))
        results = cur.fetchall()
        
        return [dict(row) for row in results]


def resolve_location(query: str) -> Optional[Dict[str, Any]]:
    """
    Resolve a location query to a canonical location using the ontology.
    Handles aliases: 'USA' -> location_id 1, 'United States' -> location_id 1
    Returns: {id: int, name: str, type: str} or None
    """
    if not query or len(query) < 2:
        return None
    
    with get_db() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # First try exact alias match
        cur.execute("""
            SELECT l.id, l.name, l.type, l.parent_id
            FROM location_aliases la
            JOIN locations l ON la.location_id = l.id
            WHERE LOWER(la.alias) = LOWER(%s)
            ORDER BY la.priority DESC
            LIMIT 1
        """, (query.strip(),))
        row = cur.fetchone()
        
        if row:
            return dict(row)
        
        # Try location name directly
        cur.execute("""
            SELECT id, name, type, parent_id
            FROM locations
            WHERE LOWER(name) = LOWER(%s)
            LIMIT 1
        """, (query.strip(),))
        row = cur.fetchone()
        
        return dict(row) if row else None


def get_location_children(parent_id: int) -> List[int]:
    """Get all child location IDs (for hierarchical search)."""
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
            WITH RECURSIVE loc_tree AS (
                SELECT id FROM locations WHERE id = %s
                UNION ALL
                SELECT l.id FROM locations l
                JOIN loc_tree lt ON l.parent_id = lt.id
            )
            SELECT id FROM loc_tree
        """, (parent_id,))
        return [row[0] for row in cur.fetchall()]


def get_recent_active_jobs(limit: int = 500) -> List[Dict]:
    """
    Fetch recent active jobs for resume matching.
    """
    query = """
        SELECT 
            j.job_id as id, j.title, j.company, j.location, j.job_description, j.date_posted,
            j.salary_min, j.salary_max, j.salary_currency as currency, j.job_link as job_url, j.is_remote,
            je.experience_min, j.visa_sponsorship,
            je.tech_languages, je.tech_frameworks, je.soft_skills
        FROM jobs j
        LEFT JOIN job_enrichment je ON j.job_id = je.job_id
        -- WHERE j.is_active = TRUE (Column missing, assume all present are active or filter by date)
        WHERE j.date_posted > now() - interval '60 days'
        ORDER BY j.date_posted DESC
        LIMIT %s;
    """
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, (limit,))
            return cur.fetchall()


def search_jobs_hybrid(
    embedding: List[float],
    min_experience: Optional[int] = None,
    location: Optional[str] = None,
    country: Optional[str] = None, # Added country filter
    tech_skills: Optional[List[str]] = None,
    limit: int = 500
) -> List[Dict]:
    """
    Stage 1 & 2: Hard Filters + Vector Similarity (pgvector).
    Returns top candidates for detailed Python scoring.
    """
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Base Query: 1 - (embedding <=> vector) is Cosine Similarity
            sql = """
                SELECT 
                    j.job_id, j.title, j.company, j.location, j.city, j.state, j.country,
                    j.is_remote, j.seniority, j.salary_min, j.salary_max, j.salary_currency,
                    j.visa_sponsorship, j.work_mode, j.job_link as job_url, 
                    je.tech_languages, je.tech_frameworks, je.tech_cloud, je.tech_tools,
                    je.soft_skills, je.experience_min, je.job_summary,
                    1 - (je.embedding <=> %s::vector) as semantic_score
                FROM job_enrichment je
                JOIN jobs j ON je.job_id = j.job_id
                WHERE je.embedding IS NOT NULL
            """
            
            params = [embedding]
            
            # --- Hard Filters (Broad Recall) ---
            
            # Country Filter (Strict)
            # Only apply if country is explicitly provided
            if country:
                if country == "United States":
                    sql += " AND (j.country ILIKE 'United States' OR j.country ILIKE 'USA' OR j.country ILIKE 'US') "
                else:
                    sql += " AND j.country ILIKE %s "
                    params.append(country)

            # SKILLS FILTER REMOVED: 
            # We rely on Vector Semantic Search to find relevant jobs found by context, not just keyword overlap.
            # detailed scoring (Stage 3) will handle the exact keyword matching.
            if tech_skills:
                # Log skills for debugging but don't filter
                logger.info(f"Hybrid Search: Target Skills={tech_skills[:5]} (Filtering Disabled for Recall)")

            # --- Vector Rank ---
            sql += """
                ORDER BY je.embedding <=> %s::vector
                LIMIT %s
            """
            params.extend([embedding, limit])
            
            cur.execute(sql, params)
            return cur.fetchall()
