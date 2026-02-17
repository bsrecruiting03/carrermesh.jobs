import os
import redis
import json
import logging
import uuid
from typing import Optional, Dict

# Configure Logging
logger = logging.getLogger("RedisManager")

class RedisQueueManager:
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.queue_key = "queue:companies:scrape"
        self.dlq_key = "queue:companies:dlq"
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            self.client.ping()
            logger.info(f"✅ Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            self.client = None

    def push_company_task(self, company: Dict) -> bool:
        """
        Pushes a company dictionary to the scraping queue.
        Adds a correlation_id for tracking.
        """
        if not self.client:
            return False
            
        # Add tracking metadata
        if "correlation_id" not in company:
            company["correlation_id"] = str(uuid.uuid4())
        if "retry_count" not in company:
            company["retry_count"] = 0
            
        payload = json.dumps(company)
        
        try:
            self.client.rpush(self.queue_key, payload)
            return True
        except Exception as e:
            logger.error(f"Failed to push company {company.get('name')}: {e}")
            return False

    def push_to_dlq(self, company: Dict, error: str) -> bool:
        """
        Moves a failed task to the Dead Letter Queue.
        """
        if not self.client:
            return False
        
        company["dlq_reason"] = error
        company["failed_at"] = str(uuid.uuid4()) # Just a placeholder or timestamp
        
        try:
            self.client.rpush(self.dlq_key, json.dumps(company))
            logger.warning(f"💀 Task moved to DLQ: {company.get('name')} | ID: {company.get('correlation_id')}")
            return True
        except Exception as e:
            logger.error(f"Failed to push to DLQ: {e}")
            return False

    def pop_company_task(self, timeout: int = 5) -> Optional[Dict]:
        """
        Pops a company task from the queue (Blocking Pop).
        """
        if not self.client:
            return None
            
        try:
            result = self.client.blpop(self.queue_key, timeout=timeout)
            if result:
                _, payload = result
                return json.loads(payload)
            return None
        except Exception as e:
            logger.error(f"Failed to pop task: {e}")
            return None

    def get_queue_status(self) -> Dict:
        """Returns queue statistics."""
        if not self.client:
            return {"error": "No Redis connection"}
            
        try:
            length = self.client.llen(self.queue_key)
            dlq_length = self.client.llen(self.dlq_key)
            return {
                "queue_length": length,
                "dlq_length": dlq_length
            }
        except Exception as e:
            return {"error": str(e)}

# Singleton instance
queue_manager = RedisQueueManager()
