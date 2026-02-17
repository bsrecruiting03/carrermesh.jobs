# Schema Analysis Report

## ❌ ISSUE IDENTIFIED

**Problem:** `sync_enrichment_to_search()` trigger references wrong column name

### Trigger Code (Line 20-21 in migration_03):
```sql
INSERT INTO job_search (job_id, title, company, location, date_posted, is_active)
SELECT job_id, title, company, location, date_posted, TRUE
```

### Actual `job_search` Table Columns:
```
✅ job_id          - EXISTS
❌ title           - Does NOT exist in job_search (not needed, comes from jobs table)
❌ company         - Does NOT exist
✅ company_id      - EXISTS (but trigger doesn't use it)
✅ company_name    - EXISTS (this is what should be used instead of 'company')
✅ location        - EXISTS
✅ date_posted     - EXISTS
✅ is_active       - EXISTS
```

### Actual `jobs` Table Columns (source):
```
✅ job_id
✅ title           - EXISTS (but not in job_search)
✅ company         - EXISTS (needs to map to job_search.company_name or company_id)
✅ location
✅ date_posted
```

## 🔧 REQUIRED FIXES

### Fix 1: Update Trigger Column Mapping

The trigger needs to:
1. **Remove** `title` from INSERT (job_search doesn't have this column)
2. **Replace** `company` with correct mapping:
   - Option A: Use `company` → `company_name` 
   - Option B: Use `company` → `company_id`

### Fix 2: Handle company_id vs company_name

Looking at job_search schema:
- `company_id` is marked as NOT NULL
- `company_name` is nullable

We need to decide:
- Does `jobs.company` contain company NAME or company ID?
- What should populate `job_search.company_id`?

## 📊 Full Column Comparison

### job_search EXPECTS (from trigger):
- job_id
- title ❌
- company ❌
- location
- date_posted
- is_active

### job_search ACTUALLY HAS:
- job_id ✅
- company_id ✅ (NOT NULL)
- title ✅ (NOT NULL - but trigger tries to insert it!)
- location ✅
- work_mode
- experience_min
- experience_max
- tech_stack_text
- job_summary
- date_posted ✅
- is_active ✅
- search_vector
- salary_min
- salary_max
- salary_currency
- visa_sponsorship
- visa_confidence
- tech_stack
- experience_years
- company_name ✅

## ✅ CORRECT TRIGGER SHOULD BE:

```sql
INSERT INTO job_search (
    job_id, 
    title,           -- EXISTS in job_search
    company_id,      -- Need to determine source
    company_name,    -- Map from jobs.company
    location, 
    date_posted, 
    is_active
)
SELECT 
    job_id, 
    title,           -- From jobs table
    company,         -- Map to company_id? Or generate?
    company,         -- Map to company_name
    location, 
    date_posted, 
    TRUE
FROM jobs
WHERE job_id = NEW.job_id
ON CONFLICT (job_id) DO NOTHING;
```

Wait - I see `title` IS in job_search (NOT NULL). Let me re-check the issue...

The error was: `column "company" of relation "job_search" does not exist`

So the actual issue is:
- Trigger uses `company` 
- But job_search has `company_name` and `company_id`, not `company`
