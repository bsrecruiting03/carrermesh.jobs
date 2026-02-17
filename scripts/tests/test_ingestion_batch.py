import sys
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure package path is correct
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "us_ats_jobs"))

# Import necessary components
from us_ats_jobs import main  # This should now be safe
from us_ats_jobs.db import database

def test_batch_ingestion(sample_size=50):
    print(f"🧪 Starting Ingestion Test (Sample Size: {sample_size})")
    
    # 1. Get Companies
    active_companies = database.get_active_companies()
    
    if not active_companies:
        print("❌ No active companies found in database!")
        return

    # Filter to ensure we have a mix (Greenhouse, Lever, etc)
    # Let's try to get non-Workday first to answer the user's doubt about "other ATS"
    # non_workday = [c for c in active_companies if c['ats_provider'] != 'workday']
    # But let's just do a random mix
    
    random.shuffle(active_companies)
    batch = active_companies[:sample_size]
    
    print(f"📊 Testing {len(batch)} companies:")
    counts = {}
    for c in batch:
        p = c['ats_provider']
        counts[p] = counts.get(p, 0) + 1
    
    for p, c in counts.items():
        print(f"   - {p}: {c}")

    print("\n🚀 Running Crawler Workers...")
    start_time = time.time()
    
    results = []
    
    # Use max 10 workers for test
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_company = {
            executor.submit(main.fetch_company_jobs, company): company 
            for company in batch
        }
        
        for future in as_completed(future_to_company):
            company = future_to_company[future]
            try:
                jobs, name, provider, success = future.result()
                results.append({
                    "name": name,
                    "provider": provider,
                    "success": success,
                    "jobs": len(jobs)
                })
                # Simple progress indicator
                sys.stdout.write("." if success else "x")
                sys.stdout.flush()
            except Exception as e:
                print(f"\n⚠️ Worker failed for {company['name']}: {e}")
                results.append({
                    "name": company['name'],
                    "provider": company['ats_provider'],
                    "success": False,
                    "jobs": 0
                })

    duration = time.time() - start_time
    print(f"\n\n⏱️  Finished in {duration:.2f} seconds")
    
    # Analyze Results
    success_count = sum(1 for r in results if r['success'])
    total_jobs = sum(r['jobs'] for r in results)
    
    print("\n📝 RESULTS Summary:")
    print(f"   ✅ Companies Scraped Successfully: {success_count}/{len(batch)}")
    print(f"   📄 Jobs Found: {total_jobs}")
    
    if success_count < len(batch):
        print("\n❌ Failures:")
        for r in results:
            if not r['success']:
                print(f"   - {r['name']} ({r['provider']})")
                
    # Specific Check for Greenhouse/Lever as requested
    gh_success = sum(1 for r in results if r['provider'] == 'greenhouse' and r['success'])
    gh_total = sum(1 for r in results if r['provider'] == 'greenhouse')
    if gh_total > 0:
        print(f"\n   🌿 Greenhouse Reliability: {gh_success}/{gh_total}")

if __name__ == "__main__":
    test_batch_ingestion(50)
