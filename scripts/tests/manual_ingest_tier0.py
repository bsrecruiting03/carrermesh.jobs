"""Manual ingestion test for specific companies"""
import sys
import os
import logging
from dotenv import load_dotenv

# Add paths to ensure us_ats_jobs and utils are found
current_file = os.path.abspath(__file__)
scripts_tests_dir = os.path.dirname(current_file) # scripts/tests
scripts_dir = os.path.dirname(scripts_tests_dir) # scripts
root_dir = os.path.dirname(scripts_dir) # root

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

load_dotenv(os.path.join(root_dir, '.env'))

# Now we can import
try:
    from us_ats_jobs.worker_scraper import process_company
    from utils.config import DB_CONFIG
    import psycopg2
except ImportError as e:
    print(f"Import Error after path fix: {e}")
    print(f"Sys Path: {sys.path}")
    raise

logging.basicConfig(level=logging.INFO)

def ingest_tier0():
    print("Fetching IDs for PayPal and Netflix...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, canonical_url, ats_provider, ats_slug 
        FROM career_endpoints 
        WHERE ats_slug IN ('paypal', 'netflix')
    """)
    endpoints = cur.fetchall()
    conn.close()
    
    for eid, url, provider, slug in endpoints:
        print(f"\n--- Ingesting {slug} (Provider: {provider}) ---")
        task = {
            "type": "endpoint_ingest",
            "endpoint_id": eid,
            "ats_provider": provider,
            "ats_slug": slug,
            "endpoint_url": url,
            "correlation_id": "manual_test_tier0"
        }
        process_company(task)

if __name__ == "__main__":
    ingest_tier0()
