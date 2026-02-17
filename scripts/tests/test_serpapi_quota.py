"""
Test script for SerpAPI Quota-Balanced Job Fetcher.
Tests quota manager and multiple adapters.
"""

import sys
import os
import logging

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Add paths
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "us_ats_jobs"))

logging.basicConfig(level=logging.INFO)

from us_ats_jobs.adapters.quota_manager import get_quota_manager
from us_ats_jobs.adapters.google import GoogleAdapter
from us_ats_jobs.adapters.microsoft import MicrosoftAdapter
from us_ats_jobs.adapters.meta import MetaAdapter

def test_quota_manager():
    """Test quota tracking."""
    print("\n=== Testing Quota Manager ===")
    qm = get_quota_manager()
    
    print(f"API Key configured: {bool(qm.api_key)}")
    print(f"Status: {qm.get_status()}")
    
    # Test quota enforcement
    for company in ["google", "microsoft", "meta"]:
        print(f"\n{company}: can_fetch={qm.can_fetch(company)}, remaining={qm.get_remaining(company)}")

def test_adapters():
    """Test adapter initialization (won't make API calls without key)."""
    print("\n=== Testing Adapters ===")
    
    qm = get_quota_manager()
    if not qm.api_key:
        print("⚠️ SERPAPI_API_KEY not set. Set it to test actual API calls.")
        print("   export SERPAPI_API_KEY=your_key_here")
        return
    
    # Test Google adapter
    print("\n--- Google Adapter ---")
    google = GoogleAdapter()
    jobs = google.fetch_jobs()
    print(f"Jobs fetched: {len(jobs)}")
    if jobs:
        print(f"Sample job: {jobs[0].get('title')} @ {jobs[0].get('company')}")
    
    # Check quota after call
    print(f"Google quota remaining: {qm.get_remaining('google')}")
    
    # Test Microsoft adapter
    print("\n--- Microsoft Adapter ---")
    msft = MicrosoftAdapter()
    jobs = msft.fetch_jobs()
    print(f"Jobs fetched: {len(jobs)}")
    if jobs:
        print(f"Sample job: {jobs[0].get('title')} @ {jobs[0].get('company')}")
    
    print(f"Microsoft quota remaining: {qm.get_remaining('microsoft')}")
    
    # Final status
    print("\n=== Final Quota Status ===")
    print(qm.get_status())

if __name__ == "__main__":
    test_quota_manager()
    test_adapters()
