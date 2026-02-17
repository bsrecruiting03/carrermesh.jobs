"""Debug script to probe Apple Jobs API"""
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)

# Apple uses their own custom system
ENDPOINTS = [
    # Apple Jobs API endpoints
    "https://jobs.apple.com/api/role/search",
    "https://jobs.apple.com/en-us/search?location=united-states-USA",
    "https://jobs.apple.com/api/v1/openings",
]

def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/html",
        "Referer": "https://jobs.apple.com/"
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
                    if isinstance(data, dict):
                        print(f"Keys: {list(data.keys())}")
                        # Apple response structure varies
                        for key in ['searchResults', 'results', 'jobs', 'data']:
                            if key in data:
                                items = data[key]
                                if isinstance(items, list):
                                    print(f"✅ Found {len(items)} in '{key}'!")
                                    if items:
                                        print(f"Sample: {json.dumps(items[0], indent=2)[:500]}")
                                    break
                    elif isinstance(data, list):
                        print(f"✅ List with {len(data)} jobs!")
                else:
                    print(f"Content-Type: {content_type}")
                    print(f"Preview: {resp.text[:200]}")
            else:
                print(f"Error: {resp.text[:200]}")
                
        except Exception as e:
            print(f"Exception: {e}")
    
    # Try POST for Apple (they may use POST)
    print("\n--- Testing POST: Apple API ---")
    try:
        payload = {
            "query": "",
            "filters": {
                "range": {"location": [{"field": "locationId", "value": "united-states-USA"}]}
            },
            "page": 1
        }
        resp = session.post(
            "https://jobs.apple.com/api/role/search",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        print(f"POST Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"Keys: {list(data.keys()) if isinstance(data, dict) else 'list'}")
            if 'searchResults' in data:
                print(f"✅ Found {len(data['searchResults'])} results!")
                if data['searchResults']:
                    print(f"Sample: {json.dumps(data['searchResults'][0], indent=2)[:500]}")
        else:
            print(f"Response: {resp.text[:300]}")
    except Exception as e:
        print(f"POST Exception: {e}")

if __name__ == "__main__":
    main()
