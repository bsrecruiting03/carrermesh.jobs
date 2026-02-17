-- Migration: Create Skills Ontology Tables (MIND Integration)
-- Version: 001
-- Date: 2026-01-31
-- Description: Adds skills, job_skills, and concepts tables for MIND Tech Ontology

-- ============================================================================
-- TABLE 1: skills - Master skills table with MIND ontology data
-- ============================================================================
CREATE TABLE IF NOT EXISTS skills (
    skill_id SERIAL PRIMARY KEY,
    canonical_name TEXT UNIQUE NOT NULL,
    skill_type TEXT[],                  -- ['Framework', 'Library', 'ProgrammingLanguage']
    synonyms TEXT[],                     -- Lowercase normalized synonyms
    technical_domains TEXT[],            -- ['Frontend', 'Backend', 'Data Science']
    implies_skills INTEGER[],            -- Array of skill_ids that this skill implies
    application_tasks TEXT[],            -- ['Authentication', 'Caching', 'Real-time Processing']
    conceptual_aspects TEXT[],           -- ['Object-Oriented', 'Functional', 'Static Typing']
    architectural_patterns TEXT[],       -- ['MVC', 'Microservices', 'Event-Driven']
    build_tools TEXT[],                  -- ['npm', 'webpack', 'gradle']
    metadata JSONB DEFAULT '{}'::JSONB,  -- Additional MIND fields
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX idx_skills_canonical ON skills (canonical_name);
CREATE INDEX idx_skills_synonyms ON skills USING GIN(synonyms);
CREATE INDEX idx_skills_type ON skills USING GIN(skill_type);
CREATE INDEX idx_skills_domains ON skills USING GIN(technical_domains);
CREATE INDEX idx_skills_implies ON skills USING GIN(implies_skills);
CREATE INDEX idx_skills_tasks ON skills USING GIN(application_tasks);

COMMENT ON TABLE skills IS 'Master skills ontology from MIND Tech Ontology with relationships and metadata';
COMMENT ON COLUMN skills.implies_skills IS 'Skills that knowing this skill implies (e.g., TypeScript implies JavaScript)';
COMMENT ON COLUMN skills.application_tasks IS 'What tasks this skill solves (e.g., Authentication, Data Validation)';

-- ============================================================================
-- TABLE 2: job_skills - Many-to-many mapping between jobs and skills
-- ============================================================================
CREATE TABLE IF NOT EXISTS job_skills (
    job_id TEXT NOT NULL,
    skill_id INTEGER NOT NULL,
    extraction_source TEXT,              -- 'title', 'description', 'requirements', 'manual'
    extraction_confidence FLOAT DEFAULT 1.0,
    matched_synonym TEXT,                 -- Which synonym was matched
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (job_id, skill_id),
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE
);

-- Indexes for job skill queries
CREATE INDEX idx_job_skills_job ON job_skills(job_id);
CREATE INDEX idx_job_skills_skill ON job_skills(skill_id);
CREATE INDEX idx_job_skills_source ON job_skills(extraction_source);
CREATE INDEX idx_job_skills_confidence ON job_skills(extraction_confidence);

COMMENT ON TABLE job_skills IS 'Many-to-many mapping of jobs to extracted skills with metadata';
COMMENT ON COLUMN job_skills.extraction_confidence IS 'Confidence score 0.0-1.0 for the skill match';

-- ============================================================================
-- TABLE 3: concepts - Application tasks, domains, and patterns
-- ============================================================================
CREATE TABLE IF NOT EXISTS concepts (
    concept_id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,              -- 'application_task', 'technical_domain', 'architectural_pattern'
    synonyms TEXT[],
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_concepts_category ON concepts(category);
CREATE INDEX idx_concepts_name ON concepts(name);
CREATE INDEX idx_concepts_synonyms ON concepts USING GIN(synonyms);

COMMENT ON TABLE concepts IS 'Conceptual aspects from MIND ontology (tasks, domains, patterns)';

-- ============================================================================
-- TABLE 4: skill_concepts - Many-to-many mapping between skills and concepts
-- ============================================================================
CREATE TABLE IF NOT EXISTS skill_concepts (
    skill_id INTEGER NOT NULL,
    concept_id INTEGER NOT NULL,
    relationship_type TEXT,              -- 'solves', 'implements', 'requires', 'associated'
    PRIMARY KEY (skill_id, concept_id),
    FOREIGN KEY (skill_id) REFERENCES skills(skill_id) ON DELETE CASCADE,
    FOREIGN KEY (concept_id) REFERENCES concepts(concept_id) ON DELETE CASCADE
);

CREATE INDEX idx_skill_concepts_skill ON skill_concepts(skill_id);
CREATE INDEX idx_skill_concepts_concept ON skill_concepts(concept_id);

COMMENT ON TABLE skill_concepts IS 'Relationships between skills and conceptual aspects';

-- ============================================================================
-- UPDATE: job_enrichment - Add columns for skill IDs and concept IDs
-- ============================================================================
ALTER TABLE job_enrichment
    ADD COLUMN IF NOT EXISTS skill_ids INTEGER[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS concept_ids INTEGER[] DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS extracted_skill_count INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_enrichment_skill_ids ON job_enrichment USING GIN(skill_ids);
CREATE INDEX IF NOT EXISTS idx_enrichment_concept_ids ON job_enrichment USING GIN(concept_ids);

COMMENT ON COLUMN job_enrichment.skill_ids IS 'Array of skill_id references from skills table';
COMMENT ON COLUMN job_enrichment.concept_ids IS 'Array of concept_id references from concepts table';

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to get all implied skills (recursive)
CREATE OR REPLACE FUNCTION get_implied_skills(input_skill_id INTEGER)
RETURNS TABLE(skill_id INTEGER, canonical_name TEXT, depth INTEGER) AS $$
WITH RECURSIVE skill_tree AS (
    -- Base case: the skill itself
    SELECT 
        s.skill_id,
        s.canonical_name,
        0 AS depth
    FROM skills s
    WHERE s.skill_id = input_skill_id
    
    UNION
    
    -- Recursive case: skills that this skill implies
    SELECT 
        implied.skill_id,
        implied.canonical_name,
        st.depth + 1
    FROM skill_tree st
    CROSS JOIN LATERAL (
        SELECT skill_id FROM unnest(
            (SELECT implies_skills FROM skills WHERE skill_id = st.skill_id)
        ) AS skill_id
    ) AS implied_ids
    JOIN skills implied ON implied.skill_id = implied_ids.skill_id
    WHERE st.depth < 3  -- Prevent infinite loops, max 3 levels deep
)
SELECT skill_id, canonical_name, depth FROM skill_tree;
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION get_implied_skills IS 'Returns all skills implied by a given skill (recursive up to 3 levels)';

-- Function to expand search query with implied skills
CREATE OR REPLACE FUNCTION expand_skill_search(skill_names TEXT[])
RETURNS TABLE(skill_id INTEGER, canonical_name TEXT) AS $$
WITH base_skills AS (
    SELECT skill_id, canonical_name
    FROM skills
    WHERE canonical_name = ANY(skill_names)
       OR synonyms && skill_names
)
SELECT DISTINCT 
    s.skill_id,
    s.canonical_name
FROM base_skills bs
CROSS JOIN LATERAL get_implied_skills(bs.skill_id) s;
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION expand_skill_search IS 'Expands skill search to include implied skills';

-- Function to find skill by synonym (case-insensitive)
CREATE OR REPLACE FUNCTION find_skill_by_synonym(search_term TEXT)
RETURNS TABLE(skill_id INTEGER, canonical_name TEXT, matched_synonym TEXT) AS $$
SELECT 
    s.skill_id,
    s.canonical_name,
    syn AS matched_synonym
FROM skills s
CROSS JOIN LATERAL unnest(s.synonyms) AS syn
WHERE LOWER(syn) = LOWER(search_term)
   OR LOWER(s.canonical_name) = LOWER(search_term)
LIMIT 1;
$$ LANGUAGE SQL STABLE;

COMMENT ON FUNCTION find_skill_by_synonym IS 'Finds a skill by exact synonym match (case-insensitive)';

-- ============================================================================
-- ANALYTICS VIEWS
-- ============================================================================

-- View: Most common skills across all jobs
CREATE OR REPLACE VIEW skill_usage_stats AS
SELECT 
    s.skill_id,
    s.canonical_name,
    s.skill_type,
    s.technical_domains,
    COUNT(js.job_id) AS job_count,
    ROUND(AVG(js.extraction_confidence)::NUMERIC, 3) AS avg_confidence
FROM skills s
LEFT JOIN job_skills js ON s.skill_id = js.skill_id
GROUP BY s.skill_id, s.canonical_name, s.skill_type, s.technical_domains
ORDER BY job_count DESC;

COMMENT ON VIEW skill_usage_stats IS 'Statistics on skill usage across jobs';

-- View: Skills by technical domain
CREATE OR REPLACE VIEW skills_by_domain AS
SELECT 
    domain,
    COUNT(*) AS skill_count,
    array_agg(canonical_name ORDER BY canonical_name) AS skills
FROM skills
CROSS JOIN LATERAL unnest(technical_domains) AS domain
GROUP BY domain
ORDER BY skill_count DESC;

COMMENT ON VIEW skills_by_domain IS 'Skills grouped by technical domain';

-- ============================================================================
-- MIGRATION ROLLBACK
-- ============================================================================

-- To rollback this migration, run:
-- DROP VIEW IF EXISTS skill_usage_stats CASCADE;
-- DROP VIEW IF EXISTS skills_by_domain CASCADE;
-- DROP FUNCTION IF EXISTS get_implied_skills(INTEGER) CASCADE;
-- DROP FUNCTION IF EXISTS expand_skill_search(TEXT[]) CASCADE;
-- DROP FUNCTION IF EXISTS find_skill_by_synonym(TEXT) CASCADE;
-- DROP TABLE IF EXISTS skill_concepts CASCADE;
-- DROP TABLE IF EXISTS concepts CASCADE;
-- DROP TABLE IF EXISTS job_skills CASCADE;
-- DROP TABLE IF EXISTS skills CASCADE;
-- ALTER TABLE job_enrichment DROP COLUMN IF EXISTS skill_ids;
-- ALTER TABLE job_enrichment DROP COLUMN IF EXISTS concept_ids;
-- ALTER TABLE job_enrichment DROP COLUMN IF EXISTS extracted_skill_count;
