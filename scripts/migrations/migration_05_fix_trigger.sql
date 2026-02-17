-- Migration 05: Fix sync_enrichment_to_search trigger
-- Issue: Trigger referenced 'company' column which doesn't exist in job_search
-- Solution: Map jobs.company to job_search.company_name and generate company_id

-- Drop and recreate the trigger function with correct column mapping
CREATE OR REPLACE FUNCTION sync_enrichment_to_search()
RETURNS TRIGGER AS $$
BEGIN
    -- Ensure row exists in job_search (Self-healing)
    -- Map jobs.company → job_search.company_name
    -- Use jobs.company as company_id for now (can be improved with actual company ID lookup)
    INSERT INTO job_search (
        job_id, 
        title, 
        company_id,
        company_name,
        location, 
        date_posted, 
        is_active
    )
    SELECT 
        job_id, 
        title,
        COALESCE(company, 'unknown'),  -- company_id (NOT NULL, so use company or 'unknown')
        company,                        -- company_name (nullable)
        location, 
        date_posted, 
        TRUE
    FROM jobs
    WHERE job_id = NEW.job_id
    ON CONFLICT (job_id) DO UPDATE SET
        title = EXCLUDED.title,
        company_name = EXCLUDED.company_name,
        location = EXCLUDED.location,
        date_posted = EXCLUDED.date_posted;

    -- Update enrichment fields from LLM data
    UPDATE job_search
    SET 
        -- Salary: Prioritize LLM extraction if not present in basic scrape
        salary_min = COALESCE(
            (SELECT salary_min FROM jobs WHERE job_id = NEW.job_id), 
            (NEW.salary_data->>'min')::INT
        ),
        salary_max = COALESCE(
            (SELECT salary_max FROM jobs WHERE job_id = NEW.job_id), 
            (NEW.salary_data->>'max')::INT
        ),
        salary_currency = COALESCE(
            (SELECT salary_currency FROM jobs WHERE job_id = NEW.job_id), 
            NEW.salary_data->>'currency'
        ),
        
        -- Visa Data: Map JSONB boolean to string
        visa_sponsorship = CASE 
            WHEN (NEW.visa_sponsorship->>'mentioned')::boolean IS TRUE THEN 'true'
            ELSE 'false' 
        END,
        visa_confidence = (NEW.visa_sponsorship->>'confidence')::FLOAT,

        -- Tech Stack: Merge all tech fields
        tech_stack = CONCAT_WS(', ', 
            NEW.tech_languages, 
            NEW.tech_frameworks, 
            NEW.tech_cloud, 
            NEW.tech_tools
        ),
        
        -- Other enrichment fields
        experience_years = NEW.experience_years,
        job_summary = NEW.summary
    WHERE job_id = NEW.job_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger already exists, no need to recreate
-- (Created by migration_03)
