"""Test Workday endpoints for Tier-0 companies (PayPal, Netflix)"""
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)

# Workday endpoints for Tier-0 companies
WORKDAY_ENDPOINTS = [
    ("PayPal", "https://paypal.wd1.myworkdayjobs.com/jobs"),
    ("Netflix", "https://netflix.wd1.myworkdayjobs.com/"),
]

def test_workday_endpoint(company, base_url):
    """Test if Workday API works for this company."""
    print(f"\n=== Testing {company} ===")
    print(f"URL: {base_url}")
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    })
    
    # Extract tenant info from URL
    # Format: https://{company}.wd{N}.myworkdayjobs.com/{path}
    parts = base_url.replace("https://", "").split(".")
    tenant = parts[0]  # e.g., "paypal" or "netflix"
    
    # Build API URL
    # Standard Workday API pattern
    api_url = f"{base_url.rstrip('/')}/wday/cxs/paypal/jobs/jobs"
    if "netflix" in base_url:
        api_url = f"https://netflix.wd1.myworkdayjobs.com/wday/cxs/netflix/en-US/jobs"
    if "paypal" in base_url:
        api_url = f"https://paypal.wd1.myworkdayjobs.com/wday/cxs/paypal/jobs/jobs"
    
    print(f"API URL: {api_url}")
    
    # Workday uses POST with JSON body
    payload = {
        "appliedFacets": {},
        "limit": 20,
        "offset": 0,
        "searchText": ""
    }
    
    try:
        resp = session.post(api_url, json=payload, timeout=30)
        print(f"Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"Keys: {list(data.keys())}")
            
            if 'jobPostings' in data:
                jobs = data['jobPostings']
                total = data.get('total', len(jobs))
                print(f"✅ Found {len(jobs)} jobs (total: {total})")
                
                if jobs:
                    job = jobs[0]
                    print(f"Sample Job: {job.get('title', 'N/A')}")
                    print(f"  Location: {job.get('locationsText', 'N/A')}")
                    print(f"  Posted: {job.get('postedOn', 'N/A')}")
                return True
            else:
                print(f"Response: {json.dumps(data, indent=2)[:500]}")
        else:
            print(f"Error: {resp.text[:300]}")
            
    except Exception as e:
        print(f"Exception: {e}")
    
    return False

def main():
    results = {}
    for company, url in WORKDAY_ENDPOINTS:
        results[company] = test_workday_endpoint(company, url)
    
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    for company, success in results.items():
        status = "✅ WORKS" if success else "❌ FAILED"
        print(f"{company}: {status}")

if __name__ == "__main__":
    main()
