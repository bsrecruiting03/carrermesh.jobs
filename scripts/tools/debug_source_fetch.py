
import sys
import os
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))

from us_ats_jobs.sources.greenhouse import fetch_greenhouse_jobs
from us_ats_jobs.utils.crawler_utils import robots_manager

def test_fetch():
    company = "stripe"
    print(f"Testing manual fetch for: {company}")
    
    # 1. Check Robots
    url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
    can = robots_manager.can_fetch(url)
    print(f"Robots check for {url}: {can}")
    
    if not can:
        print("Blocked by robots.txt logic.")
        return

    # 2. Fetch
    try:
        # Import requests to make raw call here to see what happens
        import requests
        url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        print(f"Status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('Content-Type')}")
        print(f"First 200 chars: {resp.text[:200]}")
        
        data = resp.json()
        jobs_raw = data.get("jobs", [])
        print(f"Raw Jobs from JSON: {len(jobs_raw)}")

        jobs = fetch_greenhouse_jobs(company)
        print(f"Fetched via function: {len(jobs)} jobs.")
    except Exception as e:
        print(f"Fetch failed: {e}")

if __name__ == "__main__":
    test_fetch()
