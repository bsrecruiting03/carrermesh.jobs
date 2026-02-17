-- Migration: Add Enrichment Status
-- Purpose: Track enrichment state for async processing

ALTER TABLE jobs 
ADD COLUMN IF NOT EXISTS enrichment_status VARCHAR(20) DEFAULT 'pending';
-- Values: 'pending', 'processing', 'completed', 'failed'

-- Index for fast worker polling
CREATE INDEX IF NOT EXISTS idx_jobs_enrichment_status 
ON jobs(enrichment_status) 
WHERE enrichment_status = 'pending';
