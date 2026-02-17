
-- Migration: Add soft_skills to job_enrichment and job_search

-- 1. Add column to job_enrichment
ALTER TABLE job_enrichment 
ADD COLUMN IF NOT EXISTS soft_skills TEXT[];

-- 2. Add column to job_search (denormalized)
ALTER TABLE job_search 
ADD COLUMN IF NOT EXISTS soft_skills TEXT[];

-- 3. Update the sync trigger function
CREATE OR REPLACE FUNCTION sync_enrichment() RETURNS TRIGGER AS $$
BEGIN
    UPDATE job_search
    SET 
        tech_languages = NEW.tech_languages,
        tech_frameworks = NEW.tech_frameworks,
        tech_tools = NEW.tech_tools,
        tech_cloud = NEW.tech_cloud,
        seniority = NEW.seniority,
        visa_sponsorship = (NEW.visa_sponsorship->>'mentioned')::boolean,
        salary_min = (NEW.salary->>'min')::integer,
        salary_max = (NEW.salary->>'max')::integer,
        salary_currency = NEW.salary->>'currency',
        remote_policy = NEW.remote_policy,
        experience_years = NEW.experience_years,
        job_summary = NEW.summary,
        soft_skills = NEW.soft_skills -- NEW MAPPING
    WHERE job_id = NEW.job_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
