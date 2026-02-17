"""Debug script to probe Meta (Facebook) Jobs API"""
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MetaDebugger")

# Meta Careers API endpoints to try
ENDPOINTS = [
    # Meta uses their own custom system
    "https://www.metacareers.com/graphql",
    "https://www.metacareers.com/api/jobs",
    "https://www.metacareers.com/jobs",
    # Old Facebook careers
    "https://www.facebook.com/careers/jobs",
]

def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": "https://www.metacareers.com/"
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
                    print(f"Keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
                else:
                    print(f"Content-Type: {content_type}")
                    print(f"Preview: {resp.text[:200]}")
            else:
                print(f"Error: {resp.text[:200]}")
                
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    main()
