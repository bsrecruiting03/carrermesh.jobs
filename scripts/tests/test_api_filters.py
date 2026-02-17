#!/usr/bin/env python3
"""
Test script for new API enrichment filters
Tests: visa_sponsorship, salary range, remote_policy, seniority
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_filter(name, params):
    """Test an API filter"""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"Params: {json.dumps(params, indent=2)}")
    
    try:
        response = requests.get(f"{BASE_URL}/api/jobs", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print(f"\n✅ Success!")
        print(f"   Total results: {data['total']}")
        print(f"   Page: {data['page']}/{data['pages']}")
        print(f"   Jobs returned: {len(data['jobs'])}")
        
        if data['jobs']:
            print(f"\n   Sample Job:")
            job = data[' jobs'][0]
            print(f"     • {job.get('title', 'N/A')}")
            print(f"     • {job.get('company', 'N/A')}")
            print(f"     • Salary: ${job.get('salary_min', 'N/A')} - ${job.get('salary_max', 'N/A')}")
            print(f"     • Remote: {job.get('work_mode', 'N/A')}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Error: API not running!")
        print(f"   Start the API with: cd api && uvicorn main:app --reload")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        print(f"   Response: {response.text[:200]}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def main():
    print("\n" + "="*60)
    print("API ENRICHMENT FILTERS TEST SUITE")
    print("="*60)
    
    tests = [
        ("Visa  Sponsorship Filter (true)", {
            "visa_sponsorship": "true",
            "limit": 5
        }),
        ("Salary Range Filter (100k-200k)", {
            "min_salary": 100000,
            "max_salary": 200000,
            "limit": 5
        }),
        ("Remote Policy Filter (remote)", {
            "remote_policy": "remote",
            "limit": 5
        }),
        ("Seniority Filter (senior)", {
            "seniority": "senior",
            "limit": 5
        }),
        ("Combined Filters (senior + remote + 150k+ + visa)", {
            "seniority": "senior",
            "remote_policy": "remote",
            "min_salary": 150000,
            "visa_sponsorship": "true",
            "limit": 5
        }),
        ("Tech Stack + Salary", {
            "tech_stack": "Python,React",
            "min_salary": 120000,
            "limit": 5
        })
    ]
    
    results = []
    for name, params in tests:
        success = test_filter(name, params)
        results.append((name, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")
    
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    main()
