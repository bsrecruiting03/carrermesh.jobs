import os
import sys
import logging
import json

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Setup Logging
logging.basicConfig(level=logging.INFO)

# Force Gemini
os.environ["LLM_PROVIDER"] = "gemini"
# os.environ["GEMINI_API_KEY"] = "..." # Assuming env has it

from us_ats_jobs.sources.universal import fetch_universal_jobs

def test_universal():
    # Use a known page (Greenhouse) but treat it as custom to test LLM parsing
    target_url = "https://boards.greenhouse.io/stripe" 
    company = "Stripe (Universal Test)"
    
    print(f"🧪 Testing Universal Scraper on {target_url}...")
    
    jobs = fetch_universal_jobs(company, target_url)
    
    print(f"\n✨ Extracted {len(jobs)} jobs.")
    if jobs:
        print("First 3 jobs:")
        print(json.dumps(jobs[:3], indent=2))
        
        # Verify fields
        first = jobs[0]
        if "title" in first and "location" in first:
            print("\n✅ Verification Passed: Structure looks correct.")
        else:
            print("\n❌ Verification Failed: Missing fields.")
    else:
        print("\n⚠️  No jobs found. (Might be empty page or LLM error)")

if __name__ == "__main__":
    test_universal()
