import sys
import os
import logging

# Add root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from us_ats_jobs.sources.generic import fetch_generic_jobs, normalize_generic

# Setup logging
logging.basicConfig(level=logging.INFO)

def test_walmart():
    company = "Walmart"
    # URL from the fortune500_restructured.json
    url = "https://careers.walmart.com/" 
    
    print(f"🧪 Testing Generic Scraper for {company}...")
    print(f"🔗 URL: {url}")
    
    jobs = fetch_generic_jobs(company, url)
    
    if not jobs:
        print("❌ No jobs found (Schema.org extraction returned empty).")
        print("This might be because the page doesn't use JSON-LD or blocks requests.")
    else:
        print(f"✅ Success! Found {len(jobs)} jobs.")
        print("--- Sample Job ---")
        normalized = normalize_generic(jobs[0], company)
        print(normalized)

if __name__ == "__main__":
    test_walmart()
