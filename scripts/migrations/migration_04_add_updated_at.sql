-- Add updated_at column to job_enrichment table
ALTER TABLE job_enrichment 
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();

-- Add index for faster queries
CREATE INDEX IF NOT EXISTS idx_job_enrichment_updated ON job_enrichment(updated_at DESC);
