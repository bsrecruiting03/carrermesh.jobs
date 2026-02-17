"""
Ingestion Agent (The Scheduler)

Responsibility:
1. Poll `career_endpoints` for due tasks.
2. Push tasks to Redis queue.
"""

import os
import sys
import time
import logging
import psycopg2
import json
from datetime import datetime, timedelta

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from us_ats_jobs.queue.redis_manager import queue_manager

# Force DB URL
DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

class IngestionAgent:
    def __init__(self):
        self.logger = logging.getLogger("IngestionAgent")
        self.conn = psycopg2.connect(DB_URL)
        self.conn.autocommit = True
        
    def run_scheduler_loop(self, interval=60):
        """Main loop."""
        self.logger.info("🚀 Ingestion Agent Started. Polling for endpoints...")
        
        while True:
            try:
                count = self.schedule_batch()
                if count == 0:
                    self.logger.info("💤 No endpoints due. Sleeping...")
                    time.sleep(interval)
                else:
                    self.logger.info(f"✅ Scheduled {count} endpoints. continuing...")
                    time.sleep(1) # Small pause
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"❌ Scheduler Error: {e}")
                time.sleep(30)
                
    def schedule_batch(self, batch_size=50):
        """Finds due endpoints and pushes to queue."""
        with self.conn.cursor() as cur:
            # Select endpoints not scraped in last 24h
            cur.execute("""
                SELECT id, canonical_url, ats_provider, ats_slug, created_at 
                FROM career_endpoints 
                WHERE active = TRUE 
                AND (last_ingested_at IS NULL OR last_ingested_at < NOW() - INTERVAL '24 HOURS')
                ORDER BY last_ingested_at ASC NULLS FIRST
                LIMIT %s
            """, (batch_size,))
            
            rows = cur.fetchall()
            
            if not rows:
                return 0
                
            for row in rows:
                ep_id, url, provider, slug, created_at = row
                
                # Construct Task Payload
                task = {
                    "type": "endpoint_ingest",
                    "endpoint_id": ep_id,
                    "endpoint_url": url,
                    "ats_provider": provider,
                    "ats_slug": slug or "", # Might be empty
                    "retry_count": 0,
                    "correlation_id": f"ingest-{ep_id}-{int(time.time())}"
                }
                
                # Push to Redis (reuse existing queue or new one?)
                # We reuse push_company_task but with our new payload structure
                # The worker needs to be updated to handle this new structure
                queue_manager.push_company_task(task)
                
                # Mark as scheduled (update timestamp so we don't pick it up immediately again)
                # Ideally we update to NOW(), but really we should update 'last_scheduled_at' column
                # Re-using last_ingested_at for now as a proxy or we add a column.
                # Let's just update last_ingested_at to NOW for this MVP so we don't loop forever.
                cur.execute("""
                    UPDATE career_endpoints 
                    SET last_ingested_at = NOW() 
                    WHERE id = %s
                """, (ep_id,))
                
            return len(rows)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    agent = IngestionAgent()
    agent.run_scheduler_loop()
