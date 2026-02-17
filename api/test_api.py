"""
Comprehensive test script for the Job Board API prototype.
Tests all endpoints with real database data.
"""
import requests
import json
from datetime import datetime
import sys

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def test_health():
    """Test health check endpoint."""
    print_section("TEST 1: Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2, default=str)}")
        
        assert response.status_code == 200
        assert data["status"] == "healthy"
        assert data["db_connected"] == True
        print("✅ Health check PASSED")
        return True
    except Exception as e:
        print(f"❌ Health check FAILED: {e}")
        return False

def test_job_search_basic():
    """Test basic job search without filters."""
    print_section("TEST 2: Basic Job Search (No Filters)")
    
    try:
        response = requests.get(f"{BASE_URL}/api/jobs?limit=5")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        print(f"Total Jobs: {data['total']}")
        print(f"Page: {data['page']}, Limit: {data['limit']}, Pages: {data['pages']}")
        print(f"Jobs Returned: {len(data['jobs'])}")
        
        if data['jobs']:
            print("\nFirst Job:")
            print(json.dumps(data['jobs'][0], indent=2, default=str))
        
        assert response.status_code == 200
        assert data['total'] > 0
        assert len(data['jobs']) <= 5
        print("✅ Basic search PASSED")
        return True
    except Exception as e:
        print(f"❌ Basic search FAILED: {e}")
        return False

def test_job_search_with_query():
    """Test job search with text query."""
    print_section("TEST 3: Job Search with Query (Python)")
    
    try:
        response = requests.get(f"{BASE_URL}/api/jobs?q=python&limit=5")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        print(f"Total Jobs Matching 'python': {data['total']}")
        print(f"Jobs Returned: {len(data['jobs'])}")
        
        if data['jobs']:
            print("\nSample Job Titles:")
            for job in data['jobs'][:3]:
                print(f"  - {job['title']} at {job['company']}")
        
        assert response.status_code == 200
        print("✅ Query search PASSED")
        return True
    except Exception as e:
        print(f"❌ Query search FAILED: {e}")
        return False

def test_job_search_remote():
    """Test job search with remote filter."""
    print_section("TEST 4: Job Search (Remote Only)")
    
    try:
        response = requests.get(f"{BASE_URL}/api/jobs?remote=true&limit=5")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        print(f"Total Remote Jobs: {data['total']}")
        print(f"Jobs Returned: {len(data['jobs'])}")
        
        if data['jobs']:
            for job in data['jobs'][:3]:
                print(f"  - {job['title']}: is_remote={job['is_remote']}")
                assert job['is_remote'] == True
        
        assert response.status_code == 200
        print("✅ Remote filter PASSED")
        return True
    except Exception as e:
        print(f"❌ Remote filter FAILED: {e}")
        return False

def test_job_search_location():
    """Test job search with location filter."""
    print_section("TEST 5: Job Search (Location Filter)")
    
    try:
        response = requests.get(f"{BASE_URL}/api/jobs?location=San Francisco&limit=5")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        print(f"Total Jobs in 'San Francisco': {data['total']}")
        print(f"Jobs Returned: {len(data['jobs'])}")
        
        if data['jobs']:
            for job in data['jobs'][:3]:
                print(f"  - {job['title']}: {job['location']}")
        
        assert response.status_code == 200
        print("✅ Location filter PASSED")
        return True
    except Exception as e:
        print(f"❌ Location filter FAILED: {e}")
        return False

def test_job_search_tech_stack():
    """Test job search with tech stack filter."""
    print_section("TEST 6: Job Search (Tech Stack Filter)")
    
    try:
        response = requests.get(f"{BASE_URL}/api/jobs?tech_stack=Python,Django&limit=5")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        print(f"Total Jobs with Python/Django: {data['total']}")
        print(f"Jobs Returned: {len(data['jobs'])}")
        
        if data['jobs']:
            for job in data['jobs'][:3]:
                print(f"  - {job['title']}: {job.get('tech_stack', [])}")
        
        assert response.status_code == 200
        print("✅ Tech stack filter PASSED")
        return True
    except Exception as e:
        print(f"❌ Tech stack filter FAILED: {e}")
        return False

def test_job_search_pagination():
    """Test pagination."""
    print_section("TEST 7: Job Search (Pagination)")
    
    try:
        # Page 1
        response1 = requests.get(f"{BASE_URL}/api/jobs?limit=10&page=1")
        data1 = response1.json()
        
        # Page 2
        response2 = requests.get(f"{BASE_URL}/api/jobs?limit=10&page=2")
        data2 = response2.json()
        
        print(f"Page 1: {len(data1['jobs'])} jobs")
        print(f"Page 2: {len(data2['jobs'])} jobs")
        print(f"Total: {data1['total']}, Pages: {data1['pages']}")
        
        # Verify different results
        if data1['jobs'] and data2['jobs']:
            job1_id = data1['jobs'][0]['job_id']
            job2_id = data2['jobs'][0]['job_id']
            assert job1_id != job2_id, "Pages should return different jobs"
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        print("✅ Pagination PASSED")
        return True
    except Exception as e:
        print(f"❌ Pagination FAILED: {e}")
        return False

def test_job_detail():
    """Test job detail endpoint."""
    print_section("TEST 8: Job Detail")
    
    try:
        # First, get a job ID from search
        search_response = requests.get(f"{BASE_URL}/api/jobs?limit=1")
        search_data = search_response.json()
        
        if not search_data['jobs']:
            print("⚠️  No jobs in database to test detail endpoint")
            return True
        
        job_id = search_data['jobs'][0]['job_id']
        print(f"Testing job detail for: {job_id}")
        
        # Get job detail
        detail_response = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
        print(f"Status Code: {detail_response.status_code}")
        
        data = detail_response.json()
        print(f"\nJob Title: {data['title']}")
        print(f"Company: {data['company']}")
        print(f"Location: {data.get('location', 'N/A')}")
        print(f"Description Length: {len(data.get('job_description', '')) if data.get('job_description') else 0} chars")
        
        if data.get('enrichment'):
            print(f"Enrichment Data: ✅ Present")
            print(f"  - Tech Languages: {data['enrichment'].get('tech_languages')}")
            print(f"  - Tech Frameworks: {data['enrichment'].get('tech_frameworks')}")
        
        if data.get('company_details'):
            print(f"Company Details: ✅ Present")
            print(f"  - ATS Provider: {data['company_details'].get('ats_provider')}")
        
        assert detail_response.status_code == 200
        assert data['job_id'] == job_id
        print("✅ Job detail PASSED")
        return True
    except Exception as e:
        print(f"❌ Job detail FAILED: {e}")
        return False

def test_companies_list():
    """Test companies list endpoint."""
    print_section("TEST 9: Companies List")
    
    try:
        response = requests.get(f"{BASE_URL}/api/companies?limit=5")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        print(f"Total Companies: {data['total']}")
        print(f"Companies Returned: {len(data['companies'])}")
        
        if data['companies']:
            print("\nTop 3 Companies:")
            for company in data['companies'][:3]:
                print(f"  - {company['name']} ({company['ats_provider']}): {company['active_jobs_count']} jobs")
        
        assert response.status_code == 200
        assert data['total'] > 0
        print("✅ Companies list PASSED")
        return True
    except Exception as e:
        print(f"❌ Companies list FAILED: {e}")
        return False

def test_company_detail():
    """Test company detail endpoint."""
    print_section("TEST 10: Company Detail")
    
    try:
        # Get a company ID
        list_response = requests.get(f"{BASE_URL}/api/companies?limit=1")
        list_data = list_response.json()
        
        if not list_data['companies']:
            print("⚠️  No companies in database")
            return True
        
        company_id = list_data['companies'][0]['id']
        print(f"Testing company detail for ID: {company_id}")
        
        # Get company detail
        detail_response = requests.get(f"{BASE_URL}/api/companies/{company_id}")
        print(f"Status Code: {detail_response.status_code}")
        
        data = detail_response.json()
        print(f"\nCompany: {data['name']}")
        print(f"Domain: {data.get('domain', 'N/A')}")
        print(f"ATS Provider: {data.get('ats_provider', 'N/A')}")
        print(f"Total Jobs: {data['job_count']}")
        print(f"Recent Jobs Shown: {len(data['recent_jobs'])}")
        
        assert detail_response.status_code == 200
        assert data['id'] == company_id
        print("✅ Company detail PASSED")
        return True
    except Exception as e:
        print(f"❌ Company detail FAILED: {e}")
        return False

def test_filters():
    """Test filters endpoint."""
    print_section("TEST 11: Filter Options")
    
    try:
        response = requests.get(f"{BASE_URL}/api/filters")
        print(f"Status Code: {response.status_code}")
        data = response.json()
        
        print(f"\nAvailable Filters:")
        print(f"  - Locations: {len(data['locations'])} options")
        print(f"  - Departments: {len(data['departments'])} options")
        print(f"  - Tech Languages: {len(data['tech_languages'])} options")
        print(f"  - Tech Frameworks: {len(data['tech_frameworks'])} options")
        print(f"  - ATS Providers: {len(data['ats_providers'])} options")
        print(f"  - Seniority Levels: {len(data['seniority_levels'])} options")
        print(f"  - Work Modes: {len(data['work_modes'])} options")
        
        if data['tech_languages']:
            print(f"\nSample Tech Languages: {', '.join(data['tech_languages'][:10])}")
        
        if data['ats_providers']:
            print(f"ATS Providers: {', '.join(data['ats_providers'])}")
        
        assert response.status_code == 200
        print("✅ Filters PASSED")
        return True
    except Exception as e:
        print(f"❌ Filters FAILED: {e}")
        return False

def test_error_handling():
    """Test error handling."""
    print_section("TEST 12: Error Handling")
    
    try:
        # Test 404 - job not found
        response1 = requests.get(f"{BASE_URL}/api/jobs/nonexistent_job_id_12345")
        print(f"404 Test Status Code: {response1.status_code}")
        assert response1.status_code == 404
        print("✅ 404 handling PASSED")
        
        # Test 422 - invalid query params
        response2 = requests.get(f"{BASE_URL}/api/jobs?page=-1")
        print(f"422 Test Status Code: {response2.status_code}")
        assert response2.status_code == 422
        print("✅ 422 validation PASSED")
        
        return True
    except Exception as e:
        print(f"❌ Error handling FAILED: {e}")
        return False

def run_all_tests():
    """Run all test functions."""
    print("\n" + "🚀" * 40)
    print("  JOB BOARD API - COMPREHENSIVE TEST SUITE")
    print("🚀" * 40)
    
    tests = [
        test_health,
        test_job_search_basic,
        test_job_search_with_query,
        test_job_search_remote,
        test_job_search_location,
        test_job_search_tech_stack,
        test_job_search_pagination,
        test_job_detail,
        test_companies_list,
        test_company_detail,
        test_filters,
        test_error_handling,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR in {test.__name__}: {e}")
            results.append(False)
    
    # Summary
    print_section("TEST SUMMARY")
    passed = sum(results)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        return 0
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")
        return 1

if __name__ == "__main__":
    print("\nMake sure the API server is running:")
    print("  cd api && uvicorn main:app --reload\n")
    
    input("Press Enter to start tests...")
    
    exit_code = run_all_tests()
    sys.exit(exit_code)
