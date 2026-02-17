
import os
import sys
import argparse
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from api.config import settings

def get_db_connection():
    return psycopg2.connect(settings.database_url)

def backfill_embeddings(batch_size=100, limit=None):
    print(f"🚀 Starting Embedding Backfill...")
    model = SentenceTransformer('BAAI/bge-small-en-v1.5')
    print(f"✅ Model loaded: BAAI/bge-small-en-v1.5")

    conn = get_db_connection()
    cur = conn.cursor()

    # Verify if pgvector is enabled
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()

    # Get total count of jobs needing embeddings
    cur.execute("""
        SELECT COUNT(*) 
        FROM job_enrichment je
        WHERE je.embedding IS NULL
    """)
    total_needed = cur.fetchone()[0]
    print(f"📊 Jobs needing embeddings: {total_needed}")

    if limit:
        total_needed = min(total_needed, limit)
        print(f"🛑 Limit set to: {limit}")

    processed = 0
    query = """
        SELECT 
            je.job_id, 
            j.title, 
            j.job_description,
            je.job_summary
        FROM job_enrichment je
        JOIN jobs j ON je.job_id = j.job_id
        WHERE je.embedding IS NULL
        LIMIT %s
    """
    
    while processed < total_needed:
        fetch_limit = min(batch_size, total_needed - processed)
        cur.execute(query, (fetch_limit,))
        rows = cur.fetchall()
        
        if not rows:
            break

        updates = []
        texts_to_embed = []
        job_ids = []

        for row in rows:
            job_id, title, desc, summary = row
            # Prepare text for embedding: "Title: Senior Python Dev. Summary: Experience with Django..."
            # Using summary if available, else raw description (truncated)
            text_content = summary if summary else desc[:1000]
            text = f"Title: {title}. Description: {text_content}"
            texts_to_embed.append(text)
            job_ids.append(job_id)

        # Bulk Embed
        embeddings = model.encode(texts_to_embed, normalize_embeddings=True)

        for job_id, embedding in zip(job_ids, embeddings):
            updates.append((embedding.tolist(), job_id))

        # Bulk Update using execute_values
        update_query = """
            UPDATE job_enrichment AS je
            SET embedding = v.embedding::vector
            FROM (VALUES %s) AS v(embedding, job_id)
            WHERE je.job_id = v.job_id
        """
        
        execute_values(cur, update_query, updates)
        conn.commit()
        
        processed += len(rows)
        print(f"✅ Processed {processed}/{total_needed} jobs...")

    print("🎉 Backfill Complete!")
    cur.close()
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Limit number of jobs to process")
    parser.add_argument("--batch", type=int, default=100, help="Batch size")
    args = parser.parse_args()
    
    backfill_embeddings(batch_size=args.batch, limit=args.limit)
