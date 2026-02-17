"""Debug script to probe Tesla Jobs API"""
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TeslaDebugger")

# Tesla Careers - they use Greenhouse
ENDPOINTS = [
    # Greenhouse API (Tesla uses this)
    "https://boards-api.greenhouse.io/v1/boards/tesla/jobs",
    # Direct career page API
    "https://www.tesla.com/cua-api/careers/search",
    "https://www.tesla.com/careers/search",
]

def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    })
    
    for url in ENDPOINTS:
        print(f"\n--- Testing: {url} ---")
        try:
            resp = session.get(url, timeout=15)
            print(f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if isinstance(data, dict):
                        print(f"Keys: {list(data.keys())}")
                        if 'jobs' in data:
                            jobs = data['jobs']
                            print(f"Jobs found: {len(jobs)}")
                            if jobs:
                                print(f"Sample: {json.dumps(jobs[0], indent=2)[:500]}")
                    elif isinstance(data, list):
                        print(f"List with {len(data)} items")
                        if data:
                            print(f"Sample: {json.dumps(data[0], indent=2)[:500]}")
                except:
                    print(f"Not JSON: {resp.text[:300]}")
            else:
                print(f"Error: {resp.text[:200]}")
                
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    main()
