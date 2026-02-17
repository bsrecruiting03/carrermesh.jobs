
-- Migration: Fix soft_skills type to TEXT[]

-- 1. Fix job_enrichment
ALTER TABLE job_enrichment 
ALTER COLUMN soft_skills TYPE TEXT[] USING string_to_array(soft_skills, ',');

-- 2. Fix job_search
ALTER TABLE job_search 
ALTER COLUMN soft_skills TYPE TEXT[] USING string_to_array(soft_skills, ',');
