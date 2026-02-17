import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AmazonDebugger")

AMAZON_URL = "https://www.amazon.jobs/en/search.json"

def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    })
    
    params = {"offset": 0, "result_limit": 10, "sort": "relevant", "category": "software-development", "country": "USA"}
    
    logger.info(f"Requesting: {AMAZON_URL}")
    try:
        resp = session.get(AMAZON_URL, params=params, timeout=10)
        logger.info(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            jobs = data.get('jobs', [])
            logger.info(f"Jobs Found: {len(jobs)}")
            
            # Pagination check
            # Usually strict count or next offset?
            logger.info(f"Meta Keys: {list(data.keys())}")
            
            if jobs:
                print("--- JOB 0 ---")
                print(json.dumps(jobs[0], indent=2))
        else:
            logger.info(f"Error: {resp.text[:500]}")
            
    except Exception as e:
        logger.info(f"Exception: {e}")

if __name__ == "__main__":
    main()
