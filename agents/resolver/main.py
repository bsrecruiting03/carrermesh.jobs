"""
Resolver Agent
The "Closer". Links valid but unassigned endpoints to Company records.
"""

import os
import sys
import time
import logging
import psycopg2

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

class ResolverAgent:
    def __init__(self):
        self.logger = logging.getLogger("ResolverAgent")
        self.conn = psycopg2.connect(DB_URL)
        self.conn.autocommit = True
        
    def run_resolution_loop(self, interval=300):
        """Checks for orphans every 5 minutes."""
        self.logger.info("🕵️  Resolver Agent Started. Watching for orphans...")
        
        while True:
            try:
                count = self.resolve_orphans()
                if count == 0:
                    time.sleep(interval)
                else:
                    self.logger.info(f"🔗 Resolved {count} orphans.")
                    time.sleep(10)
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.logger.error(f"❌ Resolver Error: {e}")
                time.sleep(60)

    def resolve_orphans(self):
        """Finds orphans and creates provisional companies."""
        with self.conn.cursor() as cur:
            # Find verified endpoints without company_id
            # Constraint: Only touch verified endpoints? 
            # Or assume if it's in endpoints, we want a company?
            # Let's say we resolve ANY active endpoint.
            
            cur.execute("""
                SELECT id, canonical_url, ats_provider, ats_slug
                FROM career_endpoints
                WHERE company_id IS NULL AND active = TRUE
                LIMIT 50
            """)
            orphans = cur.fetchall()
            
            if not orphans:
                return 0
                
            resolved_count = 0
            for row in orphans:
                ep_id, url, provider, slug = row
                
                # Double check if company exists (fuzzy match?)
                # For now, simplistic approach: Create Provisional
                
                name = slug.replace("-", " ").replace("_", " ").title() if slug else "Unknown Company"
                
                self.logger.info(f"🛠️  Creating Provisional Company: '{name}' for {url}")
                
                try:
                    # Insert Company
                    cur.execute("""
                        INSERT INTO companies (name, ats_url, ats_provider, active, domain)
                        VALUES (%s, %s, %s, TRUE, NULL)
                        ON CONFLICT (ats_url) DO UPDATE SET last_scraped_at = NOW() -- Just to return ID
                        RETURNING id;
                    """, (name, url, provider))
                    
                    company_id = cur.fetchone()[0]
                    
                    # Link
                    cur.execute("""
                        UPDATE career_endpoints 
                        SET company_id = %s 
                        WHERE id = %s
                    """, (company_id, ep_id))
                    
                    resolved_count += 1
                    
                except Exception as e:
                    self.logger.error(f"Failed to resolve {url}: {e}")
                    
            return resolved_count

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    agent = ResolverAgent()
    agent.run_resolution_loop()
