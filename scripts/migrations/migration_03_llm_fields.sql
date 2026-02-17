-- Migration 03: Add LLM fields and Update Sync Logic

-- 1. Add columns to job_enrichment for LLM structured output
ALTER TABLE job_enrichment 
ADD COLUMN IF NOT EXISTS visa_sponsorship JSONB,
ADD COLUMN IF NOT EXISTS salary_data JSONB,
ADD COLUMN IF NOT EXISTS remote_policy VARCHAR(50),
ADD COLUMN IF NOT EXISTS tech_tools TEXT,
ADD COLUMN IF NOT EXISTS seniority VARCHAR(50);

-- 2. Add error_log to jobs table for better debugging
ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS error_log TEXT;

-- 3. Update Sync Trigger to map LLM data to Search
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
        -- Prioritize LLM extraction for Salary if not present in basic scrape
        salary_min = COALESCE((SELECT salary_min FROM jobs WHERE job_id = NEW.job_id), (NEW.salary_data->>'min')::INT),
        salary_max = COALESCE((SELECT salary_max FROM jobs WHERE job_id = NEW.job_id), (NEW.salary_data->>'max')::INT),
        salary_currency = COALESCE((SELECT salary_currency FROM jobs WHERE job_id = NEW.job_id), NEW.salary_data->>'currency'),
        
        -- Map Visa Data
        -- job_search.visa_sponsorship is VARCHAR. We map the boolean/structure to a string summary.
        visa_sponsorship = CASE 
            WHEN (NEW.visa_sponsorship->>'mentioned')::boolean IS TRUE THEN 'true'
            ELSE 'false' 
        END,
        
        visa_confidence = (NEW.visa_sponsorship->>'confidence')::FLOAT,

        -- Enrichment fields (Merged)
        tech_stack = CONCAT_WS(', ', NEW.tech_languages, NEW.tech_frameworks, NEW.tech_cloud, NEW.tech_tools),
        experience_years = NEW.experience_years,
        job_summary = NEW.summary
    WHERE job_id = NEW.job_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
