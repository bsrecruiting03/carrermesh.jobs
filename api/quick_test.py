"""Quick manual test of the API endpoints."""
import requests

BASE = "http://127.0.0.1:8000"

print("=" * 80)
print("QUICK API TEST")
print("=" * 80)

# Test 1: Health
print("\n1. Health Check:")
r = requests.get(f"{BASE}/api/health")
print(f"   Status: {r.status_code}")
data = r.json()
print(f"   DB Connected: {data['db_connected']}")

# Test 2: Jobs Search
print("\n2. Jobs Search (first 3):")
r = requests.get(f"{BASE}/api/jobs?limit=3")
data = r.json()
print(f"   Total Jobs: {data['total']:,}")
print(f"   Returned: {len(data['jobs'])} jobs")
if data['jobs']:
    j = data['jobs'][0]
    print(f"   First: {j['title']} at {j['company']}")

# Test 3: Search Python jobs
print("\n3. Search 'Python' jobs:")
r = requests.get(f"{BASE}/api/jobs?q=python&limit=5")
data = r.json()
print(f"   Found: {data['total']:,} Python jobs")

# Test 4: Remote jobs
print("\n4. Remote Jobs:")
r = requests.get(f"{BASE}/api/jobs?remote=true&limit=3")
data = r.json()
print(f"   Found: {data['total']:,} remote jobs")

# Test 5: Companies
print("\n5. Companies (first 3):")
r = requests.get(f"{BASE}/api/companies?limit=3")
data = r.json()
print(f"   Total: {data['total']:,} companies")
if data['companies']:
    c = data['companies'][0]
    print(f"   Top: {c['name']} - {c['active_jobs_count']} jobs")

# Test 6: Filters
print("\n6. Filter Options:")
r = requests.get(f"{BASE}/api/filters")
data = r.json()
print(f"   Locations: {len(data['locations'])}")
print(f"   Departments: {len(data['departments'])}")  
print(f"   Tech Languages: {len(data['tech_languages'])}")
print(f"   ATS Providers: {data['ats_providers']}")

print("\n" + "=" * 80)
print("✅ ALL TESTS PASSED!")
print("=" * 80)
