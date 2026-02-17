
import sys
import os
import json
import requests

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../us_ats_jobs")))

from us_ats_jobs.sources.greenhouse import fetch_greenhouse_jobs
from us_ats_jobs.sources.lever import fetch_lever_jobs
from us_ats_jobs.sources.ashby import fetch_ashby_jobs
from us_ats_jobs.sources.workable import fetch_workable_jobs
from us_ats_jobs.sources.bamboohr import fetch_bamboohr_jobs
from us_ats_jobs.sources.usajobs import fetch_usajobs_jobs
from us_ats_jobs.sources.jsearch import fetch_jsearch_jobs
from us_ats_jobs.sources.workday import fetch_workday_jobs

def test_ats(provider, company):
    print(f"\nAudit: Testing {provider} for {company}")
    try:
        if provider == "greenhouse":
            jobs = fetch_greenhouse_jobs(company)
        elif provider == "lever":
            jobs = fetch_lever_jobs(company)
        elif provider == "ashby":
            jobs = fetch_ashby_jobs(company)
        elif provider == "workable":
            jobs = fetch_workable_jobs(company)
        elif provider == "bamboohr":
            jobs = fetch_bamboohr_jobs(company)
        elif provider == "workday":
            jobs = fetch_workday_jobs(company)
        elif provider == "usajobs":
            from us_ats_jobs.config import USAJOBS_API_KEY, USAJOBS_EMAIL
            jobs = fetch_usajobs_jobs(USAJOBS_API_KEY, USAJOBS_EMAIL, query=company)
        else:
            print(f"Unknown provider: {provider}")
            return

        print(f"✅ Success: Fetched {len(jobs)} jobs.")
        if jobs:
            print(f"Sample Job Title: {jobs[0].get('title') or jobs[0].get('text')}")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python audit_ats.py <provider> <company>")
        sys.exit(1)
    
    provider = sys.argv[1].lower()
    company = sys.argv[2]
    test_ats(provider, company)
