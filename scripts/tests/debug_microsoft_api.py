import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MicrosoftDebugger")

# Microsoft Careers API
URL = "https://gcsservices.careers.microsoft.com/search/api/v1/search"

def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://careers.microsoft.com/",
        "Origin": "https://careers.microsoft.com",
        "Content-Type": "application/json",
        "Accept": "application/json"
    })
    
    # Microsoft uses POST with JSON body
    payload = {
        "q": "",
        "pg": 1,
        "pgSz": 20,
        "l": "en_us"
    }
    
    logger.info(f"Requesting (POST): {URL}")
    try:
        resp = session.post(URL, json=payload, timeout=15)
        logger.info(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            logger.info(f"Keys: {list(data.keys())}")
            
            # Microsoft structure varies
            if 'operationResult' in data:
                res = data['operationResult'].get('result', {})
                jobs = res.get('jobs', [])
                logger.info(f"Jobs Found: {len(jobs)}")
                logger.info(f"Total: {res.get('totalJobs')}")
                
                if jobs:
                    print("--- JOB 0 ---")
                    print(json.dumps(jobs[0], indent=2))
            else:
                # Direct structure
                print(json.dumps(data, indent=2)[:2000])
                
        else:
            logger.info(f"Error: {resp.text[:500]}")
            
    except Exception as e:
        logger.info(f"Exception: {e}")

if __name__ == "__main__":
    main()

