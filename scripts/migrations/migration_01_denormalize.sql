-- Migration: Denormalize Enrichment Data into Job Search
-- Purpose: Speed up search by removing 3-way joins

-- 1. Add Columns to job_search (Search Projection)
ALTER TABLE job_search 
ADD COLUMN IF NOT EXISTS salary_min INT,
ADD COLUMN IF NOT EXISTS salary_max INT,
ADD COLUMN IF NOT EXISTS salary_currency VARCHAR(10),
ADD COLUMN IF NOT EXISTS visa_sponsorship VARCHAR(50), 
ADD COLUMN IF NOT EXISTS visa_confidence FLOAT,
ADD COLUMN IF NOT EXISTS tech_stack TEXT, -- Comma-separated or space-separated for simple search
ADD COLUMN IF NOT EXISTS experience_years FLOAT,
ADD COLUMN IF NOT EXISTS job_summary TEXT;

-- 2. Create Trigger Function to Keep Data in Sync
CREATE OR REPLACE FUNCTION sync_enrichment_to_search()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure row exists (Self-healing)
    INSERT INTO job_search (job_id, title, company, location, date_posted, is_active)
    SELECT job_id, title, company, location, date_posted, TRUE
    FROM jobs
    WHERE job_id = NEW.job_id
    ON CONFLICT (job_id) DO NOTHING;

    UPDATE job_search
    SET 
        salary_min = (SELECT salary_min FROM jobs WHERE job_id = NEW.job_id),
        salary_max = (SELECT salary_max FROM jobs WHERE job_id = NEW.job_id),
        salary_currency = (SELECT salary_currency FROM jobs WHERE job_id = NEW.job_id),
        visa_sponsorship = (SELECT visa_sponsorship FROM jobs WHERE job_id = NEW.job_id),
        visa_confidence = (SELECT visa_confidence FROM jobs WHERE job_id = NEW.job_id),
        -- Enrichment fields
        tech_stack = CONCAT_WS(', ', NEW.tech_languages, NEW.tech_frameworks, NEW.tech_cloud, NEW.tech_tools),
        experience_years = NEW.experience_years,
        job_summary = NEW.summary
    WHERE job_id = NEW.job_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Create Trigger on job_enrichment
DROP TRIGGER IF EXISTS trigger_sync_enrichment ON job_enrichment;
CREATE TRIGGER trigger_sync_enrichment
AFTER INSERT OR UPDATE ON job_enrichment
FOR EACH ROW EXECUTE FUNCTION sync_enrichment_to_search();

-- 4. Backfill Existing Data
-- Update from Jobs table first (Salary, Visa)
UPDATE job_search s
SET 
    salary_min = j.salary_min,
    salary_max = j.salary_max,
    salary_currency = j.salary_currency,
    visa_sponsorship = j.visa_sponsorship,
    visa_confidence = j.visa_confidence
FROM jobs j
WHERE s.job_id = j.job_id;

-- Update from Enrichment table (Skills, Summary)
UPDATE job_search s
SET 
    tech_stack = CONCAT_WS(', ', e.tech_languages, e.tech_frameworks, e.tech_cloud, e.tech_tools),
    experience_years = e.experience_years,
    job_summary = e.summary
FROM job_enrichment e
WHERE s.job_id = e.job_id;
