-- Migration: Add embedding column for vector search
-- Purpose: Enable hybrid search (semantic matching) between resumes and jobs

-- 1. Enable pgvector extension (idempotent)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Add embedding column to job_enrichment
-- BAAI/bge-small-en-v1.5 output dimension is 384
ALTER TABLE job_enrichment 
ADD COLUMN IF NOT EXISTS embedding vector(384);

-- 3. Create HNSW index for fast similarity search
-- vector_cosine_ops is best for cosine similarity (1 - cosine_distance)
CREATE INDEX IF NOT EXISTS idx_job_enrichment_embedding 
ON job_enrichment USING hnsw (embedding vector_cosine_ops);
