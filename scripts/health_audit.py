import os
import sys
import logging
import psycopg2
from datetime import datetime, timedelta
import meilisearch

# Configuration
PG_URL = os.getenv("DATABASE_URL")
MEILI_URL = os.getenv("MEILI_URL")
MEILI_KEY = os.getenv("MEILI_MASTER_KEY")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [HEALTH] - %(levelname)s - %(message)s')
logger = logging.getLogger("HealthAudit")

def check_db_health():
    try:
        conn = psycopg2.connect(PG_URL)
        cur = conn.cursor()
        
        # 1. Enrichment Coverage
        cur.execute("SELECT count(*) FROM jobs;")
        total_jobs = cur.fetchone()[0]
        
        cur.execute("SELECT count(*) FROM jobs WHERE enrichment_status = 'completed';")
        enriched_jobs = cur.fetchone()[0]
        
        coverage = (enriched_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        # 2. Sync Lag
        cur.execute("SELECT (value->>'timestamp') FROM system_metadata WHERE key = 'meilisearch_last_sync';")
        last_sync_str = cur.fetchone()
        last_sync = datetime.fromisoformat(last_sync_str[0]) if last_sync_str else None
        
        lag_minutes = 0
        if last_sync:
            lag = datetime.now() - last_sync
            lag_minutes = lag.total_seconds() / 60

        # 3. Failed Jobs
        cur.execute("SELECT count(*) FROM jobs WHERE enrichment_status = 'failed';")
        failed_jobs = cur.fetchone()[0]

        logger.info(f"📊 DB Status: {enriched_jobs}/{total_jobs} enriched ({coverage:.2f}%)")
        logger.info(f"📊 Failed Jobs: {failed_jobs}")
        logger.info(f"📊 Sync Lag: {lag_minutes:.2f} minutes")

        conn.close()
        return {
            "total_jobs": total_jobs,
            "enriched_jobs": enriched_jobs,
            "failed_jobs": failed_jobs,
            "sync_lag_minutes": lag_minutes,
            "healthy": coverage > 95 and lag_minutes < 120
        }
    except Exception as e:
        logger.error(f"❌ DB Health Check Failed: {e}")
        return {"healthy": False, "error": str(e)}

def check_search_health():
    try:
        client = meilisearch.Client(MEILI_URL, MEILI_KEY)
        stats = client.index('jobs').get_stats()
        
        # Meilisearch client returns an object/dict depending on version
        if hasattr(stats, 'number_of_documents'):
            doc_count = stats.number_of_documents
        elif isinstance(stats, dict):
            doc_count = stats.get('numberOfDocuments', 0)
        else:
            # Fallback to dict conversion
            doc_count = getattr(stats, 'number_of_documents', 0)
        
        logger.info(f"🔍 Search Index Status: {doc_count} documents")
        return {"search_doc_count": doc_count, "healthy": doc_count > 0}
    except Exception as e:
        logger.error(f"❌ Search Health Check Failed: {e}")
        return {"healthy": False, "error": str(e)}

def run_audit():
    logger.info("🩺 Starting Production Health Audit...")
    db_status = check_db_health()
    search_status = check_search_health()
    
    # Parity Check
    if db_status.get("healthy") and search_status.get("healthy"):
        diff = abs(db_status["total_jobs"] - search_status["search_doc_count"])
        parity = (1 - (diff / db_status["total_jobs"])) * 100 if db_status["total_jobs"] > 0 else 0
        logger.info(f"⚖️ Sync Parity: {parity:.2f}% (Diff: {diff} jobs)")
        
        if parity < 99:
            logger.warning("⚠️ Sync Parity is below 99%! Manual sync advised.")
    
    if db_status["healthy"] and search_status["healthy"]:
        logger.info("✅ SYSTEM HEALTHY")
    else:
        logger.error("🚨 SYSTEM UNHEALTHY - CHECK LOGS")
        sys.exit(1)

if __name__ == "__main__":
    run_audit()
