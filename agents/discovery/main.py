import os
import sys
import logging
import time
import psycopg2
from urllib.parse import urlparse

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Force DB URL
DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

# Basic Fingerprints
ATS_FINGERPRINTS = {
    "greenhouse": ["boards.greenhouse.io", "greenhouse.io"],
    "lever": ["jobs.lever.co"],
    "ashby": ["jobs.ashbyhq.com", "ashbyhq.com"],
    "workable": ["apply.workable.com"],
    "bamboohr": [".bamboohr.com/careers", ".bamboohr.com/jobs"],
    "workday": ["myworkdayjobs.com"]
}

class DiscoveryAgent:
    def __init__(self):
        self.logger = logging.getLogger("DiscoveryAgent")
        self.conn = psycopg2.connect(DB_URL)
        self.conn.autocommit = True
        
    def fingerprint_url(self, url):
        """Identify ATS provider from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        full_url = url.lower()
        
        for provider, patterns in ATS_FINGERPRINTS.items():
            for pattern in patterns:
                if pattern in domain or pattern in full_url:
                    return provider
        return "generic"

    def register_endpoint(self, url, source="manual"):
        """Register a discovered endpoint."""
        provider = self.fingerprint_url(url)
        
        # Normalize
        canonical = url.strip()
        if not canonical.startswith("http"):
            canonical = f"https://{canonical}"
            
        # Extract slug heuristic
        slug = None
        try:
             path = urlparse(canonical).path.strip("/")
             if path: slug = path.split("/")[-1]
        except: pass

        self.logger.info(f"🔍 Discovered: {canonical} ({provider}) via {source}")
        
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO career_endpoints (
                        canonical_url, ats_provider, ats_slug, 
                        active, verification_status, confidence_score,
                        discovered_from
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (canonical_url) DO NOTHING
                """, (
                    canonical, 
                    provider, 
                    slug, 
                    True, 
                    'pending_verification', 
                    0.5, # Lower confidence for scraped
                    source
                ))
                
                if cur.rowcount > 0:
                    self.logger.info(f"   ✅ Registered new endpoint: {canonical}")
                    return True
                else:
                    self.logger.info(f"   ⏭️  Endpoint already exists: {canonical}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"   ❌ Failed to register {canonical}: {e}")
            return False

    def close(self):
         self.conn.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    agent = DiscoveryAgent()
    try:
        # Test Cases
        agent.register_endpoint("https://boards.greenhouse.io/stripe", "test_run")
        agent.register_endpoint("jobs.lever.co/openai", "test_run")
    finally:
        agent.close()
