# MIND Ontology Integration - Deployment Guide

## 📋 Overview

This guide walks through deploying the MIND Tech Ontology integration (Phase 1 + Phase 2) to production.

**Timeline**: 3-4 hours total deployment time

---

## ✅ Pre-Deployment Checklist

### 1. Prerequisites
- [ ] PostgreSQL 12+ running
- [ ] Python 3.8+ installed
- [ ] All dependencies installed: `pip install -r requirements.txt`
- [ ] Database backup created: `pg_dump job_board > backup_$(date +%Y%m%d).sql`
- [ ] MIND ontology files downloaded in project root

### 2. Verification
- [ ] Run: `python -c "import psycopg2; print('OK')"`
- [ ] Verify database connectivity: `psql -h localhost -p 5433 -U postgres -d job_board -c "SELECT 1"`
- [ ] Check disk space: Minimum 500MB free for new tables

---

## 🚀 Deployment Steps

### Step 1: Database Migration (10 minutes)

```bash
# Apply migration
psql -h localhost -p 5433 -U postgres -d job_board -f migrations/001_create_skills_ontology_tables.sql

# Verify tables created
psql -h localhost -p 5433 -U postgres -d job_board -c "\dt skills*"
psql -h localhost -p 5433 -U postgres -d job_board -c "\dt concepts*"
psql -h localhost -p 5433 -U postgres -d job_board -c "\dt job_skills*"
```

**Expected Output**:
```
           List of relations
 Schema |       Name       | Type  |  Owner   
--------+------------------+-------+----------
 public | skills           | table | postgres
 public | job_skills       | table | postgres
 public | concepts         | table | postgres
 public | skill_concepts   | table | postgres
```

### Step 2: Frequency Analysis (30 minutes)

```bash
# Analyze existing jobs to determine which skills to import
python scripts/analyze_skill_frequency.py \
    --output data/skill_frequency.json \
    --mind-file MIND-tech-ontology-main/__aggregated_skills.json

# Review top skills
head -100 data/skill_frequency.json
```

**What to check**:
- Total jobs analyzed should match your database count
- Top 20 skills should look reasonable (Python, JavaScript, etc.)
- Frequency threshold recommendations will be shown

### Step 3: Import MIND Ontology (15 minutes)

```bash
# DRY RUN FIRST - preview what will be imported
python scripts/import_mind_ontology.py \
    --frequency-file data/skill_frequency.json \
    --min-frequency 10 \
    --phase both \
    --dry-run

# Review output, then run actual import
python scripts/import_mind_ontology.py \
    --frequency-file data/skill_frequency.json \
    --min-frequency 10 \
    --phase both

# Verify import
psql -h localhost -p 5433 -U postgres -d job_board -c "SELECT COUNT(*) FROM skills;"
psql -h localhost -p 5433 -U postgres -d job_board -c "SELECT COUNT(*) FROM concepts;"
```

**Expected Results**:
- Skills imported: ~1,200-1,500 (after frequency filtering)
- Concepts imported: ~100-150
- Skill-concept mappings: ~3,000-5,000

### Step 4: Backfill Existing Jobs (60-120 minutes)

```bash
# DRY RUN FIRST
python scripts/backfill_job_skills.py \
    --batch-size 1000 \
    --limit 100 \
    --dry-run

# Run full backfill (this will take time)
python scripts/backfill_job_skills.py \
    --batch-size 1000

# Monitor progress in another terminal
watch -n 5 'psql -h localhost -p 5433 -U postgres -d job_board -c "SELECT COUNT(*) FROM job_skills;"'
```

**Performance**:
- ~10,000 jobs: 15 minutes
- ~50,000 jobs: 60 minutes
- ~100,000 jobs: 120 minutes

**If interrupted**: Resume with:
```bash
python scripts/backfill_job_skills.py \
    --batch-size 1000 \
    --start-from 50000  # Adjust based on where it stopped
```

### Step 5: Run Tests (10 minutes)

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run regression tests
pytest tests/test_mind_integration.py -v

# Check for any failures
# Expected: All tests pass
```

**Critical tests**:
- ✅ `test_golden_dataset_precision` - Should be ≥80%
- ✅ `test_golden_dataset_recall` - Should be ≥85%
- ✅ `test_search_latency` - Should be <200ms

### Step 6: Verify Data Quality (5 minutes)

```sql
-- Check skill coverage
SELECT 
    COUNT(*) FILTER (WHERE skill_ids IS NOT NULL) * 100.0 / COUNT(*) AS coverage_pct,
    AVG(array_length(skill_ids, 1)) AS avg_skills_per_job
FROM job_enrichment;

-- Expected: 
-- coverage_pct: >80%
-- avg_skills_per_job: 6-12

-- Top extracted skills
SELECT * FROM skill_usage_stats LIMIT 20;

-- Verify hierarchical relationships
SELECT 
    s1.canonical_name AS parent,
    array_agg(s2.canonical_name) AS implies
FROM skills s1
CROSS JOIN unnest(s1.implies_skills) AS implied_id
JOIN skills s2 ON s2.skill_id = implied_id
GROUP BY s1.canonical_name
LIMIT 10;
```

### Step 7: A/B Test Configuration (5 minutes)

Create feature flag in your application:

```python
# config.py
FEATURES = {
    'use_mind_ontology': True,  # Set to False to rollback
    'use_skill_expansion': True,
    'expansion_depth': 2
}
```

Update your job ingestion pipeline:

```python
# us_ats_jobs/intelligence/enrich_jobs.py

from us_ats_jobs.intelligence.skills_db import SkillExtractorDB

def enrich_job(job_data, db_config):
    if FEATURES['use_mind_ontology']:
        # New MIND-based extraction
        extractor = SkillExtractorDB(db_config)
        skills = extractor.extract(job_data['description'])
        
        return {
            'skill_ids': [s.skill_id for s in skills],
            'tech_languages': [s.canonical_name for s in skills],  # Backward compat
            'extracted_skill_count': len(skills)
        }
    else:
        # Fallback to old system
        return extract_skills_legacy(job_data)
```

---

## 📊 Post-Deployment Monitoring

### Metrics to Track

**1. Search Quality Metrics** (Week 1)

```sql
-- Zero-result search rate
SELECT 
    COUNT(*) FILTER (WHERE result_count = 0) * 100.0 / COUNT(*) AS zero_result_pct
FROM search_logs
WHERE created_at > NOW() - INTERVAL '7 days';

-- Target: <6% (down from ~12% before)

-- Average results per search
SELECT AVG(result_count)
FROM search_logs
WHERE created_at > NOW() - INTERVAL '7 days';

-- Target: >25 (up from ~15 before)
```

**2. Performance Metrics**

```sql
-- Search latency p95
SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY response_time_ms)
FROM search_logs
WHERE created_at > NOW() - INTERVAL '1 day';

-- Target: <150ms
```

**3. Skill Coverage**

```sql
-- Daily skill extraction quality
SELECT 
    date_trunc('day', j.ingested_at) AS date,
    COUNT(*) AS jobs,
    AVG(je.extracted_skill_count) AS avg_skills
FROM jobs j
JOIN job_enrichment je ON j.job_id = je.job_id
WHERE j.ingested_at > NOW() - INTERVAL '7 days'
GROUP BY date
ORDER BY date DESC;
```

### Expected Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Zero-result searches | 12% | <6% | -50% |
| Avg results per search | 15 | 25+ | +67% |
| Skill coverage | 70% | 85%+ | +15pp |
| Search latency (p95) | 120ms | <150ms | Similar |

---

## 🔧 Troubleshooting

### Issue 1: Import Fails with "Out of Memory"

**Solution**: Reduce batch size
```bash
python scripts/import_mind_ontology.py \
    --batch-size 50 \  # Reduced from 100
    --min-frequency 10
```

### Issue 2: Backfill is Too Slow

**Solution**: Increase batch size or run in parallel
```bash
# Terminal 1
python scripts/backfill_job_skills.py --batch-size 2000 --start-from 0 --limit 50000

# Terminal 2
python scripts/backfill_job_skills.py --batch-size 2000 --start-from 50000 --limit 50000
```

### Issue 3: Search Returns Too Few Results

**Check**: Is expansion enabled?
```python
# In your search API
search = HierarchicalJobSearch(DB_CONFIG, use_expansion=True)  # ← MUST be True
```

### Issue 4: High False Positive Rate

**Solution**: Adjust confidence thresholds
```sql
-- Remove low-confidence matches
DELETE FROM job_skills WHERE extraction_confidence < 0.8;
```

---

## 🔄 Rollback Procedure

**If something goes wrong**:

```bash
# 1. Restore database backup
psql -h localhost -p 5433 -U postgres -d job_board < backup_YYYYMMDD.sql

# 2. Or manually drop new tables
psql -h localhost -p 5433 -U postgres -d job_board <<EOF
DROP VIEW IF EXISTS skill_usage_stats CASCADE;
DROP VIEW IF EXISTS skills_by_domain CASCADE;
DROP FUNCTION IF EXISTS get_implied_skills(INTEGER) CASCADE;
DROP FUNCTION IF EXISTS expand_skill_search(TEXT[]) CASCADE;
DROP FUNCTION IF EXISTS find_skill_by_synonym(TEXT) CASCADE;
DROP TABLE IF EXISTS skill_concepts CASCADE;
DROP TABLE IF EXISTS concepts CASCADE;
DROP TABLE IF EXISTS job_skills CASCADE;
DROP TABLE IF EXISTS skills CASCADE;
ALTER TABLE job_enrichment DROP COLUMN IF EXISTS skill_ids;
ALTER TABLE job_enrichment DROP COLUMN IF EXISTS concept_ids;
ALTER TABLE job_enrichment DROP COLUMN IF EXISTS extracted_skill_count;
EOF

# 3. Disable feature flag
FEATURES['use_mind_ontology'] = False
```

**Time to rollback**: <5 minutes

---

## ✨ Success Criteria

Deployment is successful if:

- ✅ All tests pass (`pytest tests/test_mind_integration.py`)
- ✅ Skill coverage >80% (`SELECT COUNT(*) ... FROM job_enrichment WHERE skill_ids IS NOT NULL`)
- ✅ Search latency <150ms p95
- ✅ Zero-result searches <6%
- ✅ No errors in application logs for 24 hours

---

## 📞 Support

If you encounter issues:

1. Check logs: `tail -f logs/application.log`
2. Verify database state: Run verification queries above
3. Review test output: `pytest tests/test_mind_integration.py -v --tb=long`

---

## 🎉 Next Steps After Deployment

1. **Week 1**: Monitor metrics dashboard daily
2. **Week 2**: Gather user feedback on search quality
3. **Month 1**: Analyze A/B test results
4. **Month 2**: Consider Phase 3 (concepts) if Phase 1+2 successful
5. **Quarterly**: Update MIND ontology:
   ```bash
   cd MIND-tech-ontology-main
   git pull origin main
   python scripts/import_mind_updates.py --incremental
   ```

---

**Deployment Date**: _____________  
**Deployed By**: _____________  
**Rollback Plan Tested**: ☐ Yes ☐ No
