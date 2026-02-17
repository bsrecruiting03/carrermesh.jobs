"""Debug script to probe TikTok/ByteDance Jobs API"""
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TikTokDebugger")

# TikTok/ByteDance Careers API endpoints
ENDPOINTS = [
    # TikTok careers
    "https://careers.tiktok.com/api/v1/search/job",
    "https://careers.tiktok.com/api/v1/job/list",
    # ByteDance (parent company)
    "https://jobs.bytedance.com/api/v1/search/job",
]

def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://careers.tiktok.com/"
    })
    
    for url in ENDPOINTS:
        print(f"\n--- Testing GET: {url} ---")
        try:
            resp = session.get(url, timeout=15)
            print(f"Status: {resp.status_code}")
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    print(f"Response: {json.dumps(data, indent=2)[:500]}")
                except:
                    print(f"Not JSON: {resp.text[:200]}")
            else:
                print(f"Response: {resp.text[:200]}")
                
        except Exception as e:
            print(f"Exception: {e}")
    
    # Try POST for TikTok (they often use POST)
    print("\n--- Testing POST: TikTok API ---")
    try:
        payload = {
            "keyword": "",
            "limit": 20,
            "offset": 0,
            "portal_type": 1
        }
        resp = session.post(
            "https://careers.tiktok.com/api/v1/search/job",
            json=payload,
            timeout=15
        )
        print(f"POST Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
            if 'data' in data:
                print(f"Data keys: {list(data['data'].keys()) if isinstance(data['data'], dict) else 'list/other'}")
        else:
            print(f"Error: {resp.text[:300]}")
    except Exception as e:
        print(f"POST Exception: {e}")

if __name__ == "__main__":
    main()
