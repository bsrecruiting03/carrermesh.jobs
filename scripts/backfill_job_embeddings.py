
import os
import sys
import psycopg2
from psycopg2.extras import execute_values
import logging
from tqdm import tqdm

# Add root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from us_ats_jobs.intelligence.extractor_layer2 import Layer2VectorExtractor

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BackfillEmbeddings")

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/job_board")

def backfill_embeddings():
    logger.info("🚀 Starting Embedding Backfill...")
    
    # 1. Initialize Extractor (Loads Model)
    extractor = Layer2VectorExtractor()
    if extractor.model is None:
        logger.error("❌ Failed to load model. Exiting.")
        return

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # 2. Fetch jobs without embeddings
    # We join jobs for title/description
    logger.info("🔍 Fetching target jobs...")
    cur.execute("""
        SELECT j.job_id, j.title, j.job_description 
        FROM jobs j
        LEFT JOIN job_enrichment je ON j.job_id = je.job_id
        WHERE je.embedding IS NULL
        AND j.job_description IS NOT NULL
    """)
    rows = cur.fetchall()
    total = len(rows)
    logger.info(f"🎯 Found {total} jobs needing embeddings.")

    if total == 0:
        logger.info("✅ All jobs already have embeddings.")
        return

    # 3. Process in batches
    BATCH_SIZE = 100
    updates = []
    
    for i, (job_id, title, description) in enumerate(tqdm(rows)):
        text = f"{title}. {description}"
        embedding = extractor.embed_text(text)
        
        if embedding:
            updates.append((embedding, job_id))
            
        if len(updates) >= BATCH_SIZE:
            _flush_batch(cur, conn, updates)
            updates = []
            
    # Final flush
    if updates:
        _flush_batch(cur, conn, updates)

    logger.info("✅ Backfill Complete.")
    conn.close()

def _flush_batch(cur, conn, updates):
    if not updates: return
    try:
        execute_values(cur, """
            UPDATE job_enrichment 
            SET embedding = data.embedding::vector
            FROM (VALUES %s) AS data (embedding, job_id)
            WHERE job_enrichment.job_id = data.job_id
        """, updates)
        conn.commit()
    except Exception as e:
        logger.error(f"❌ Batch update failed: {e}")
        conn.rollback()

if __name__ == "__main__":
    backfill_embeddings()
