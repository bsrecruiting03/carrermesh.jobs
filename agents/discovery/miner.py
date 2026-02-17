"""
Link Miner Strategy
Scans existing job descriptions for links that look like ATS endpoints.
"""

import re
import logging
import psycopg2

class LinkMiner:
    def __init__(self, agent):
        self.agent = agent
        self.logger = logging.getLogger("DiscoveryAgent.LinkMiner")
        
    def mine_jobs(self, limit=1000):
        """Scan recent jobs for outbound links."""
        self.logger.info(f"⛏️  Mining last {limit} jobs for new endpoints...")
        
        try:
            with self.agent.conn.cursor() as cur:
                # Get job descriptions
                cur.execute("""
                    SELECT job_description 
                    FROM jobs 
                    ORDER BY date_posted DESC 
                    LIMIT %s
                """, (limit,))
                descriptions = cur.fetchall()
                
                found_count = 0
                for (desc,) in descriptions:
                    if not desc: continue
                    
                    # Regex for URLs
                    urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', desc)
                    for url in urls:
                        # Heuristic: verify if it looks like an ATS
                        provider = self.agent.fingerprint_url(url)
                        if provider != "generic":
                            if self.agent.register_endpoint(url, source="link_miner"):
                                found_count += 1
                                
                self.logger.info(f"⛏️  Mining complete. Found {found_count} new endpoints.")
                return found_count
                
        except Exception as e:
            self.logger.error(f"Mining failed: {e}")
            return 0
