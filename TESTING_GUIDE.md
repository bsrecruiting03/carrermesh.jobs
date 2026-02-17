# 🧪 ATS Testing Guide

## Overview

This guide explains how to test your ATS integrations to ensure they're working correctly before running large-scale job fetches.

---

## 📋 Test Suite: `test_ats.py`

Comprehensive test suite that validates:
- **Fetchers** - Can retrieve jobs from ATS APIs
- **Normalizers** - Convert raw data to standard format
- **Data Quality** - All required fields are present and valid

---

## 🚀 Quick Start

### Run All Tests
```bash
python test_ats.py
```

### Test Specific Provider
```bash
python test_ats.py --provider greenhouse
python test_ats.py --provider lever
python test_ats.py --provider ashby
python test_ats.py --provider workable
python test_ats.py --provider bamboohr
```

### Verbose Output
```bash
python test_ats.py --verbose
```

---

## 📊 Test Results Interpretation

### ✅ PASS
- Fetcher successfully retrieved jobs
- Normalizer converted them to standard format
- All required fields present and valid

**Example:**
```
✅ PASS | LEVER | 139 jobs
```

### ❌ FAIL
Possible reasons:
1. **No jobs returned** - Company may not be hiring or URL changed
2. **Fetch error** - API endpoint down or changed
3. **Normalization error** - Data structure changed
4. **Validation error** - Missing required fields

**Example:**
```
❌ FAIL | WORKABLE | 0 jobs
```

---

## 🔍 What the Tests Check

### Required Fields
Every normalized job MUST have:
- `job_id` - Unique identifier
- `title` - Job title
- `company` - Company name
- `location` - Job location
- `job_description` - Job description
- `job_link` - URL to application
- `source` - ATS provider name

### Field Validation
- **Not None** - Field exists and has value
- **Not Empty** - Strings are not blank
- **URL Format** - job_link starts with http:// or https://
- **Source Match** - Source field matches ATS provider

---

## 📝 Example Test Output

```
🧪 ATS INTEGRATION TEST SUITE 🧪

============================================================
🧪 TESTING GREENHOUSE
============================================================
📍 Testing company: stripe
✅ Fetched 538 raw jobs
✅ Normalized 538 jobs

📊 Validation Results:
   Total jobs: 538
   Valid jobs: 10
   Invalid jobs: 0

============================================================
🧪 TESTING LEVER
============================================================
📍 Testing company: spotify
✅ Fetched 139 raw jobs
✅ Normalized 139 jobs

📊 Validation Results:
   Total jobs: 139
   Valid jobs: 10
   Invalid jobs: 0

============================================================
📊 TEST SUMMARY
============================================================
✅ PASS | GREENHOUSE   | 538 jobs
✅ PASS | LEVER        | 139 jobs
✅ PASS | ASHBY        | 115 jobs
❌ FAIL | WORKABLE     | 0 jobs
❌ FAIL | BAMBOOHR     | 0 jobs

------------------------------------------------------------
Total: 5 tests | Passed: 3 | Failed: 2
============================================================
```

---

## 🛠️ Test Companies

The test suite uses known working companies:

| ATS | Test Company | Why |
|-----|--------------|-----|
| Greenhouse | stripe | Large company, always hiring |
| Lever | spotify | Public API, stable |
| Ashby | notion | Popular, reliable |
| Workable | canva | Design company |
| BambooHR | benevity | HR software company |

**You can modify these** in `test_ats.py`:
```python
TEST_COMPANIES = {
    "greenhouse": "your-company",
    "lever": "another-company",
    # ...
}
```

---

## 🐛 Troubleshooting

### Test Failed: "No jobs returned"

**Possible causes:**
1. Company not currently hiring
2. Company changed ATS provider
3. Company slug name changed

**Solution:**
```python
# Try a different company
TEST_COMPANIES = {
    "greenhouse": "airbnb",  # instead of stripe
}
```

### Test Failed: "Fetch failed"

**Possible causes:**
1. API endpoint changed
2. Rate limiting
3. Network error
4. Authentication required (new)

**Solution:**
1. Check if fetcher code needs update
2. Verify API endpoint: `https://api.lever.co/v3/postings/spotify`
3. Add delays between requests

### Test Failed: "Validation error"

**Possible causes:**
1. Normalizer not handling new API fields
2. API response format changed
3. Missing error handling

**Solution:**
1. Check raw job data structure
2. Update normalizer function
3. Add null checks

---

## 📈 When to Run Tests

### Before Major Changes
```bash
# Baseline before changes
python test_ats.py > test_results_before.txt

# Make changes to fetchers/normalizers

# Verify nothing broke
python test_ats.py > test_results_after.txt
diff test_results_before.txt test_results_after.txt
```

### Regular Health Checks
```bash
# Weekly cron job
0 0 * * 0 cd /path/to/project && python test_ats.py
```

### After API Updates
If an ATS provider changes their API:
```bash
python test_ats.py --provider greenhouse
```

---

## 🔧 Extending the Tests

### Add New Test Company

```python
# test_ats.py

TEST_COMPANIES = {
    "greenhouse": "stripe",
    "lever": "spotify",
    "my_new_company": "company-slug"  # Add here
}
```

### Add Custom Validation

```python
# test_ats.py

def validate_custom(job, provider):
    """Custom validation logic"""
    errors = []
    
    # Example: Ensure title is not too short
    if len(job.get("title", "")) < 5:
        errors.append("Title too short")
    
    # Example: Ensure location is formatted correctly
    location = job.get("location", "")
    if "," not in location:
        errors.append("Location missing city/state")
    
    return errors
```

### Test Multiple Companies

```python
# test_multiple_companies.py

TEST_COMPANIES_LIST = {
    "greenhouse": ["stripe", "airbnb", "coinbase"],
    "lever": ["spotify", "netflix", "shopify"],
}

for provider, companies in TEST_COMPANIES_LIST.items():
    for company in companies:
        test_result = test_provider(provider, company)
        print(f"{provider}/{company}: {test_result}")
```

---

## 💡 Best Practices

### 1. Run Tests Before Production
```bash
# Development workflow
git pull
python test_ats.py  # Ensure tests pass
python us_ats_jobs/main.py  # Run job fetch
```

### 2. Monitor Test Results Over Time
```bash
# Save results with timestamp
python test_ats.py > logs/test_$(date +%Y%m%d).txt
```

### 3. Use CI/CD Integration
```yaml
# .github/workflows/test.yml
name: ATS Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - run: python test_ats.py
```

### 4. Create Alerts for Failures
```bash
# test_with_alerts.sh
if ! python test_ats.py; then
    echo "ATS tests failed!" | mail -s "Alert" admin@company.com
    exit 1
fi
```

---

## 📊 Success Criteria

### Production Ready
- ✅ All 5 ATS tests passing
- ✅ At least 10 jobs returned per provider
- ✅ Zero validation errors
- ✅ All required fields populated

### Investigation Needed
- ⚠️ Less than 5 jobs returned
- ⚠️ Some validation errors
- ⚠️ Intermittent failures

### Broken
- ❌ Zero jobs returned
- ❌ Fetch errors
- ❌ All validation errors
- ❌ Consistent failures

---

## 🔄 Test Maintenance

### Monthly
- Review test companies (still hiring?)
- Update test data expectations
- Check for API changes

### Quarterly
- Add new ATS providers
- Update validation rules
- Review error patterns

### Annually
- Refactor test suite
- Add integration tests
- Performance benchmarks

---

## 📚 Related Files

- [`test_ats.py`](file:///c:/Users/DELL/OneDrive/Desktop/job%20board%20-%20version%202/test_ats.py) - Main test suite
- `us_ats_jobs/sources/*.py` - ATS fetchers
- `us_ats_jobs/normalizer.py` - Data normalizers
- `us_ats_jobs/main.py` - Production job fetcher

---

## ✅ Checklist

Before running production job fetch:

- [ ] Run `python test_ats.py`
- [ ] All tests passing ✅
- [ ] Review any warnings ⚠️
- [ ] Check job counts reasonable
- [ ] Validate sample job data
- [ ] Verify database connectivity
- [ ] Check disk space for jobs
- [ ] Confirm API keys valid
- [ ] Review circuit breaker status

**Then:**
```bash
python us_ats_jobs/main.py  # Safe to run!
```

---

**Last Updated:** 2026-01-20  
**Test Suite Version:** 1.0  
**Supported ATS:** Greenhouse, Lever, Ashby, Workable, BambooHR
