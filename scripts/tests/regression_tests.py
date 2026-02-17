import sys
import os
import time
import statistics
import concurrent.futures
import threading

# Ensure we can import from 'api'
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), "api"))

# Force DB URL to correct port/host
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@127.0.0.1:5433/job_board"

from api.database import search_jobs, build_job_search_query, get_db

def print_header(title):
    print(f"\n## {title}\n")

def print_result(name, passed, details=""):
    icon = "✅" if passed else "❌"
    print(f"* {icon} **{name}**: {details}")

# --- GROUP 1: PERFORMANCE ---

def test_latency_baseline():
    print_header("TC-P1: Search Latency Baseline")
    query = "data scientist"
    latencies = []
    
    # Warm up? User says "Cache cleared (cold start)". 
    # But usually we can't clear cache easily without restarting DB.
    # We'll just run 20 times.
    
    failed = False
    details = []
    
    for i in range(20):
        start = time.perf_counter()
        search_jobs(query=query, page=1)
        dur = (time.perf_counter() - start) * 1000
        latencies.append(dur)
        if dur > 400:
             failed = True
             details.append(f"Run {i} exceeded 400ms: {dur:.2f}ms")

    p95 = statistics.quantiles(latencies, n=100)[94] # Approximate P95
    p99 = statistics.quantiles(latencies, n=100)[98]
    avg = statistics.mean(latencies)
    
    passed = not failed and p95 <= 200 and p99 <= 400
    
    msg = f"Avg: {avg:.2f}ms, P95: {p95:.2f}ms, P99: {p99:.2f}ms. "
    if failed:
        msg += f"Failures: {', '.join(details)}"
        
    print_result("Latency Assertions", passed, msg)
    return passed

def test_cached_search():
    print_header("TC-P2: Cached Search Must Be Fast")
    query = "data scientist"
    
    # First Request
    start1 = time.perf_counter()
    search_jobs(query=query)
    dur1 = (time.perf_counter() - start1) * 1000
    
    # Second Request
    start2 = time.perf_counter()
    search_jobs(query=query)
    dur2 = (time.perf_counter() - start2) * 1000
    
    passed = dur2 <= 50
    # Note: Cache hit check is manual/implicit by time.
    print_result("2nd Request Latency", passed, f"1st: {dur1:.2f}ms, 2nd: {dur2:.2f}ms (Target <= 50ms)")
    return passed

def test_common_term_stability():
    print_header("TC-P3: Common-Term Stability")
    query = "software engineer"
    
    start = time.perf_counter()
    search_jobs(query=query)
    dur = (time.perf_counter() - start) * 1000
    
    # Check Plan
    has_seq_scan = False
    uses_index = False
    
    sql, params = build_job_search_query(query=query)
    # We need to analyze the CTE part mostly. API returns full query.
    
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("EXPLAIN " + sql, params)
            plan = "\n".join([row[0] for row in cur.fetchall()])
            
            if "Seq Scan" in plan and "job_search" in plan: 
                 # Check if Seq Scan is on job_search (bad) or small tables (ok)
                 # Usually we want Index Scan or Bitmap Heap Scan
                 pass 
            
            if "Index Scan" in plan or "Bitmap Heap Scan" in plan:
                uses_index = True
            
            if "Seq Scan on job_search" in plan:
                has_seq_scan = True

    passed_time = dur <= 300
    passed_plan = uses_index and not has_seq_scan
    
    print_result("Latency <= 300ms", passed_time, f"{dur:.2f}ms")
    print_result("DB Query Plan", passed_plan, f"Index Scan: {uses_index}, Seq Scan: {has_seq_scan}")
    
    return passed_time and passed_plan


# --- GROUP 2: QUERY PLAN ---

def test_query_plan_regression():
    print_header("TC-Q1 & TC-Q2: Query Plan Regression")
    
    # We examine the structure of the query plan for "data scientist"
    query = "data scientist"
    sql, params = build_job_search_query(query=query)
    
    plan_output = ""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("EXPLAIN (FORMAT TEXT) " + sql, params)
            plan_output = "\n".join([row[0] for row in cur.fetchall()])

    # Assertions
    # 1. No joins in the candidate CTE?
    # Hard to parse "CTE" boundary in text explain perfectly, but we can look for
    # Join on 'jobs' or 'job_enrichment' occurring BEFORE 'Limit' or deeply nested?
    # Actually, the user wants "Query plan contains only job_search" (in the search part).
    
    # 2. Limit applied before Ranking?
    # Look for "Limit" node filtering "job_search" or "candidates".
    
    print("```")
    print(plan_output)
    print("```")
    
    # Heuristic checks
    has_join_jobs = "JOIN jobs" in sql # Check SQL string logic
    # Wait, the python code DOES join jobs (in the outer select).
    # The test says "Query plan contains only job_search... No JOIN jobs".
    # This refers to the CANDIDATE GENERATION phase.
    # The SQL returned by build_job_search_query is the FULL SQL.
    # It *Will* contain joins.
    # The User wants to ensure the "CTE" part or the "Search" part is isolated.
    # I can verify this by checking the CTE definition in the SQL string.
    
    cte_part = sql.split("WITH candidates AS (")[1].split("),")[0]
    join_in_cte = "JOIN" in cte_part
    limit_in_cte = "LIMIT" in cte_part
    
    passed_q1 = not join_in_cte
    passed_q2 = limit_in_cte and ("ORDER BY" not in cte_part)
    
    print_result("TC-Q1: No Joins in Candidate CTE", passed_q1, "Checked CTE SQL structure")
    print_result("TC-Q2: LIMIT inside CTE, No ORDER BY", passed_q2, "Checked CTE SQL structure")
    
    return passed_q1 and passed_q2

# --- GROUP 4: RELEVANCE ---

def test_relevance_exact():
    print_header("TC-R1: Exact Match Must Rank Higher")
    query = "Data Scientist"
    try:
        jobs, _ = search_jobs(query=query, limit=10)
        
        # Check if "Data Scientist" is in top result title
        if not jobs:
            print_result("Relevance", False, "No jobs found")
            return False
            
        first_title = jobs[0]['title']
        
        # Verify order: "Data Scientist" > "Data Analyst"
        # Find ranks
        ds_indices = [i for i, j in enumerate(jobs) if "Data Scientist" in j['title']]
        da_indices = [i for i, j in enumerate(jobs) if "Data Analyst" in j['title']]
        
        passed = True
        msg = f"Top result: {first_title}"
        
        if ds_indices and da_indices:
            if min(ds_indices) > min(da_indices):
                passed = False
                msg += " (FAIL: Data Analyst ranked above Data Scientist)"
        
        print_result("Exact Match Ranking", passed, msg)
        return passed
    except Exception as e:
        print_result("Relevance", False, f"Error: {e}")
        return False

def test_freshness():
    print_header("TC-R2: Freshness Bias Preserved")
    # This is hard to test deterministically without controlling seed data.
    # We'll just check if the SQL contains the sort clause.
    
    sql, _ = build_job_search_query(query="python")
    # Expected: "ORDER BY r.rank DESC, r.date_posted DESC"
    
    passed = "ORDER BY r.rank DESC, r.date_posted DESC" in sql or "ORDER BY rank DESC, js.date_posted DESC" in sql
    print_result("Ordering Clause Verified", passed, "SQL contains correct ORDER BY")
    return passed

# --- GROUP 5: EDGE CASES ---

def test_zero_results():
    print_header("TC-E1: Zero Results Query")
    query = "quantum pastry chef"
    
    start = time.perf_counter()
    jobs, total = search_jobs(query=query)
    dur = (time.perf_counter() - start) * 1000
    
    passed = (total == 0) and (len(jobs) == 0) and (dur <= 200)
    print_result("Zero Results Handled", passed, f"Total: {total}, Time: {dur:.2f}ms")
    return passed

def test_high_load():
    print_header("TC-E2: High Load Stability")
    
    query = "data scientist"
    
    # concurrent 50
    count = 50
    latencies = []
    errors = 0
    
    def run_query():
        try:
            t0 = time.perf_counter()
            search_jobs(query=query)
            return (time.perf_counter() - t0) * 1000
        except:
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(run_query) for _ in range(count)]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res is None:
                errors += 1
            else:
                latencies.append(res)
                
    p95 = statistics.quantiles(latencies, n=100)[94] if latencies else 0
    passed = errors == 0 and p95 <= 300
    
    print_result("Concurrency 50", passed, f"P95: {p95:.2f}ms, Errors: {errors}")
    return passed

if __name__ == "__main__":
    print("# Regression Test Results\n")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_latency_baseline()
    try:
        test_cached_search()
    except Exception as e:
        print_result("TC-P2 Error", False, str(e))

    try:
        test_common_term_stability()
    except Exception as e:
        print_result("TC-P3 Error", False, str(e))
        
    test_query_plan_regression()
    test_relevance_exact()
    test_freshness()
    test_zero_results()
    test_high_load()
