"""Debug script to probe Netflix Jobs API"""
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)

# Netflix uses Lever for their careers
ENDPOINTS = [
    # Lever API (Netflix uses this)
    "https://api.lever.co/v0/postings/netflix",
    "https://jobs.lever.co/netflix",
    # Direct Netflix jobs
    "https://jobs.netflix.com/api/search",
    "https://jobs.netflix.com/search",
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
                content_type = resp.headers.get('content-type', '')
                if 'json' in content_type:
                    data = resp.json()
                    if isinstance(data, list):
                        print(f"✅ List with {len(data)} jobs!")
                        if data:
                            print(f"Sample: {json.dumps(data[0], indent=2)[:600]}")
                    elif isinstance(data, dict):
                        print(f"Keys: {list(data.keys())}")
                        if 'records' in data:
                            print(f"✅ Found {len(data['records'])} records!")
                else:
                    print(f"Content-Type: {content_type}")
                    print(f"Preview: {resp.text[:200]}")
            else:
                print(f"Error: {resp.text[:200]}")
                
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    main()
