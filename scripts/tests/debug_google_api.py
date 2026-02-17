import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GoogleDebugger")

# Google Careers API v1
URL = "https://careers.google.com/api/v1/jobs/search/"

def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    })
    
    # Common query to trigger results
    params = {
        "page": 1, 
        "page_size": 20,
        "q": "" # Empty query for everything
    }
    
    logger.info(f"Requesting: {URL}")
    try:
        resp = session.get(URL, params=params, timeout=10)
        logger.info(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            # Inspect keys
            logger.info(f"Keys: {list(data.keys())}")
            
            jobs = data.get('jobs', [])
            logger.info(f"Jobs Found: {len(jobs)}")
            logger.info(f"Count/Page info: count={data.get('count')}, next_page={data.get('next_page_token')}")
            
            if jobs:
                print("--- JOB 0 ---")
                print(json.dumps(jobs[0], indent=2))
        else:
            logger.info(f"Error: {resp.text[:500]}")
            
    except Exception as e:
        logger.info(f"Exception: {e}")

if __name__ == "__main__":
    main()
