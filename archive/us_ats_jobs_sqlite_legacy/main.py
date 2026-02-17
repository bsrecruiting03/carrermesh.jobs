import os
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# -------- SOURCE FETCHERS --------
from sources.greenhouse import fetch_greenhouse_jobs
from sources.lever import fetch_lever_jobs
from sources.jsearch import fetch_jsearch_jobs
from sources.linkedin_rapidapi import fetch_linkedin_jobs
from sources.ashby import fetch_ashby_jobs
from sources.workable import fetch_workable_jobs
from sources.usajobs import fetch_usajobs_jobs
from sources.workday import fetch_workday_jobs
from sources.bamboohr import fetch_bamboohr_jobs
import db.database as database
database.create_tables()


# -------- NORMALIZERS --------
from normalizer import (
    normalize_greenhouse,
    normalize_lever,
    normalize_jsearch,
    normalize_linkedin,
    normalize_ashby,
    normalize_workable,
    normalize_usajobs,
    normalize_workday,
    normalize_bamboohr,
)
from utils.crawler_utils import robots_manager, UserAgentRotator

# -------- CONFIG --------
from config import (
    JSEARCH_API_KEY,
    LINKEDIN_API_KEY,
    USAJOBS_API_KEY,
    USAJOBS_EMAIL,
    ENABLE_LINK_USAJOBS,
    ENABLE_LINKED_WORKDAY,
    ENABLE_BAMBOOHR,
    ENABLE_LINKEDIN,
    ENABLE_JSEARCH,
    ENABLE_ATS,
    USAJOBS_PAGES,
    USAJOBS_KEYWORDS,
    JSEARCH_PAGES,
    LINKEDIN_PAGES,
    MAX_WORKERS,
    GREENHOUSE_COMPANIES,
    LEVER_COMPANIES,
    ASHBY_COMPANIES,
    WORKABLE_COMPANIES,
    WORKDAY_COMPANIES,
)

# -------- STATE --------
all_jobs = []
jobs_lock = Lock()  # Thread-safe lock for shared state

source_counts = {
    "greenhouse": 0,
    "lever": 0,
    "ashby": 0,
    "jsearch": 0,
    "linkedin_rapidapi": 0,
    "workable": 0,
    "usajobs": 0,
    "workday": 0,
    "bamboohr": 0,
}

# -------- WORKER FUNCTION FOR PARALLEL PROCESSING --------
def fetch_company_jobs(company_data):
    """
    Worker function to fetch jobs from a single company.
    Returns (jobs_list, company_name, provider, success_status)
    """
    name = company_data["name"]
    company_id = company_data["id"]
    provider = company_data["ats_provider"]
    
    jobs_list = []
    
    # Robots.txt compliance check
    # Construct base URL for the ATS to check robots.txt
    if provider == "greenhouse":
        base_url = f"https://boards-api.greenhouse.io/v1/boards/{name}/jobs"
    elif provider == "lever":
        base_url = f"https://api.lever.co/v3/postings/{name}"
    elif provider == "ashby":
        base_url = f"https://api.ashbyhq.com/posting-api/job-board/{name}"
    else:
         # Fallback or generic Workable check
         base_url = f"https://apply.workable.com/api/v1/widget/accounts/{name}"

    if not robots_manager.can_fetch(base_url):
        print(f"🤖 Robots.txt restriction for {name} ({provider}) — skipping")
        return [], name, provider, False

    try:
        if provider == "greenhouse":
            print(f"Fetching Greenhouse jobs for {name}")
            jobs = fetch_greenhouse_jobs(name)
            for job in jobs:
                normalized = normalize_greenhouse(job, name)
                jobs_list.append(normalized)
            
            # CRITICAL FIX: Insert into JOBS table first to satisfy FK for raw_jobs
            if jobs_list:
                database.insert_jobs(jobs_list)
                for i, job in enumerate(jobs):
                    database.save_raw_job(jobs_list[i]['job_id'], 'greenhouse', job)

            database.record_company_success(company_id)
            return jobs_list, name, provider, True
        
        elif provider == "lever":
            print(f"Fetching Lever jobs for {name}")
            jobs = fetch_lever_jobs(name)
            for job in jobs:
                normalized = normalize_lever(job, name)
                jobs_list.append(normalized)
            
            if jobs_list:
                database.insert_jobs(jobs_list)
                for i, job in enumerate(jobs):
                    database.save_raw_job(jobs_list[i]['job_id'], 'lever', job)

            database.record_company_success(company_id)
            return jobs_list, name, provider, True

        elif provider == "ashby":
            print(f"Fetching Ashby jobs for {name}")
            jobs = fetch_ashby_jobs(name)
            for job in jobs:
                normalized = normalize_ashby(job, name)
                jobs_list.append(normalized)
            
            if jobs_list:
                database.insert_jobs(jobs_list)
                for i, job in enumerate(jobs):
                    database.save_raw_job(jobs_list[i]['job_id'], 'ashby', job)

            database.record_company_success(company_id)
            return jobs_list, name, provider, True

        elif provider == "workable":
            print(f"Fetching Workable jobs for {name}")
            jobs = fetch_workable_jobs(name)
            for job in jobs:
                normalized = normalize_workable(job, name)
                jobs_list.append(normalized)
            
            if jobs_list:
                database.insert_jobs(jobs_list)
                for i, job in enumerate(jobs):
                    database.save_raw_job(jobs_list[i]['job_id'], 'workable', job)

            database.record_company_success(company_id)
            return jobs_list, name, provider, True
            
        elif provider == "workday":
            print(f"Fetching Workday jobs for {name}")
            # Workday needs the slug for URL construction
            # If name is 'Mastercard', we need its entry from config or database slug
            # For now, we assume 'name' in active_companies contains the slug if it's workday
            jobs = fetch_workday_jobs(name) or []
            for job in jobs:
                all_jobs.append(normalize_workday(job, name, name))
            database.record_company_success(company_id)
            return jobs_list, name, provider, True
            
        elif provider == "bamboohr":
            print(f"Fetching BambooHR jobs for {name}")
            jobs = fetch_bamboohr_jobs(name)
            for job in jobs:
                normalized = normalize_bamboohr(job, name)
                database.save_raw_job(normalized['job_id'], 'bamboohr', job)
                jobs_list.append(normalized)
            database.record_company_success(company_id)
            return jobs_list, name, provider, True

    except Exception as e:
        # Check if it's a 404 error (company doesn't use this ATS)
        error_msg = str(e)
        is_404 = "404" in error_msg or "Not Found" in error_msg
        
        if is_404:
            print(f"⚠️ {provider} 404 for {name} — skipping")
            database.record_company_failure(company_id)
        else:
            print(f"⚠️ {provider} failed for {name}")
            print("Reason:", error_msg)
        
        return [], name, provider, False

# -------- ATS SOURCES (PARALLEL) --------
def run_crawler():
    global all_jobs, source_counts
    
    # -------- ATS SOURCES (PARALLEL) --------
    if ENABLE_ATS:
        active_companies = database.get_active_companies()
        print(f"Loaded {len(active_companies)} active companies from database")
        
        # Filter out Workday companies if disabled
        if not ENABLE_LINKED_WORKDAY:
            workday_count = sum(1 for c in active_companies if c.get('ats_provider') == 'workday')
            active_companies = [c for c in active_companies if c.get('ats_provider') != 'workday']
            if workday_count > 0:
                print(f"🚫 Skipping {workday_count} Workday companies (ENABLE_LINKED_WORKDAY=False)")
        
        # Filter out BambooHR companies if disabled
        if not ENABLE_BAMBOOHR:
            bamboohr_count = sum(1 for c in active_companies if c.get('ats_provider') == 'bamboohr')
            active_companies = [c for c in active_companies if c.get('ats_provider') != 'bamboohr']
            if bamboohr_count > 0:
                print(f"🚫 Skipping {bamboohr_count} BambooHR companies (ENABLE_BAMBOOHR=False)")
        
        # Show circuit breaker stats
        open_circuits = database.get_companies_with_open_circuits()
        if open_circuits:
            print(f"⏸️  {len(open_circuits)} companies with open circuits (skipped)")
        
        print(f"🚀 Fetching jobs in parallel with {MAX_WORKERS} workers...\n")
        
        # Parallel execution with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all tasks
            future_to_company = {
                executor.submit(fetch_company_jobs, company): company 
                for company in active_companies
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_company):
                jobs_list, name, provider, success = future.result()
                
                # Thread-safe update to shared state
                with jobs_lock:
                    all_jobs.extend(jobs_list)
                    source_counts[provider] += len(jobs_list)

    # -------- USAJOBS --------
    if ENABLE_LINK_USAJOBS:
        print("\n--- Fetching USAJOBS (Federal Jobs) ---")
        for kw in USAJOBS_KEYWORDS:
            jobs = fetch_usajobs_jobs(USAJOBS_API_KEY, USAJOBS_EMAIL, query=kw, pages=USAJOBS_PAGES)
            for job in jobs:
                all_jobs.append(normalize_usajobs(job))
                source_counts["usajobs"] += 1

    # -------- JSEARCH --------
    if ENABLE_JSEARCH:
        try:
            # Pre-load existing companies to avoid re-discovering them
            try:
                 active_companies_list = database.get_active_companies()
                 known_companies = {c['name'].lower() for c in active_companies_list}
            except:
                 known_companies = set()
                 
            print(f"Known companies before JSearch: {len(known_companies)}")

            # Import discovery agent
            from scripts.discover_companies import discover_and_save

            for page in range(1, JSEARCH_PAGES + 1):
                print(f"Fetching JSearch page {page}")
                jobs = fetch_jsearch_jobs(JSEARCH_API_KEY, page)
                for job in jobs:
                    all_jobs.append(normalize_jsearch(job))
                    source_counts["jsearch"] += 1
                    
                    # 2. FEEDER SYSTEM: Check if we should discover this company
                    employer = job.get("employer_name")
                    if employer:
                        cleaned_name = employer.strip()
                        # Simple filter to avoid staffing agencies or generic names if possible?
                        # For now just check duplicates.
                        if cleaned_name.lower() not in known_companies:
                            print(f"🆕 JSearch found new company: {cleaned_name}. Triggering discovery...")
                            # Trigger discovery (will save to DB if found)
                            discover_and_save(cleaned_name)
                            # Add to local cache so we don't try again this run
                            known_companies.add(cleaned_name.lower())

        except Exception as e:
            print("⚠️ JSearch failed — continuing")
            print("Reason:", str(e))

    # -------- LINKEDIN (BEST EFFORT) --------
    if ENABLE_LINKEDIN:
        try:
            print("Fetching LinkedIn RapidAPI jobs")
            for page in range(1, LINKEDIN_PAGES + 1):
                jobs = fetch_linkedin_jobs(LINKEDIN_API_KEY, page)
                for job in jobs:
                    all_jobs.append(normalize_linkedin(job))
                    source_counts["linkedin_rapidapi"] += 1
        except Exception as e:
            print("⚠️ LinkedIn RapidAPI failed — continuing without it")
            print("Reason:", str(e))

    # -------- EXPORT --------
    df = pd.DataFrame(all_jobs)

    if not df.empty:
        df.drop_duplicates(subset=["job_id"], inplace=True)

    # ---------------- EXCEL EXPORT (OPTIONAL / DEBUG) ----------------
    #os.makedirs("output", exist_ok=True)
    #df.to_excel("output/us_jobs_final.xlsx", index=False)

    # --------------- DATABASE INSERTION ----------------
    from db.database import insert_jobs

    inserted = insert_jobs(df.to_dict(orient="records"))

    print(f"\nStored {inserted} jobs in database")

    print("\n📊 Job Source Breakdown:")
    for source, count in source_counts.items():
        print(f"  - {source}: {count}")

if __name__ == "__main__":
    run_crawler()
