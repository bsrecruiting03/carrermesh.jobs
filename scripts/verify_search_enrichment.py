import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SearchVerification")

BASE_URL = "http://localhost:8000"

def verify_search():
    # 1. Search for "Python"
    # We'll use the generic search first
    logger.info("Searching for 'Python'...")
    try:
        response = requests.get(f"{BASE_URL}/api/jobs", params={"query": "Python", "limit": 5})
        response.raise_for_status()
        data = response.json()
        jobs = data.get("jobs", [])
        total = data.get("total", 0)
        
        logger.info(f"Total results for 'Python': {total}")
        for job in jobs:
            print(f"- {job['title']} @ {job['company']} (ID: {job['job_id']})")
            print(f"  Tech Stack: {job.get('tech_stack')}")
            
    except Exception as e:
        logger.error(f"Search failed: {e}")

    # 2. Check a specific job detail for enrichment
    if jobs:
        job_id = jobs[0]['job_id']
        logger.info(f"Checking details for job {job_id}...")
        try:
            detail_res = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
            detail_res.raise_for_status()
            job_detail = detail_res.json()
            print(f"Job Summary: {job_detail.get('job_summary')[:100]}...")
            print(f"Enrichment: {json.dumps(job_detail.get('enrichment', {}), indent=2)}")
        except Exception as e:
            logger.error(f"Detail fetch failed: {e}")

if __name__ == "__main__":
    verify_search()
