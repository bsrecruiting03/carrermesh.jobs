import requests
import logging
import concurrent.futures
import time
import sys
import os
import re

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agents.discovery.main import DiscoveryAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("WorkdayEngine")

class WorkdayScanner:
    def __init__(self):
        self.agent = DiscoveryAgent()
        self.base_domain = "myworkdayjobs.com"
        self.shards = ["", ".wd1", ".wd3", ".wd5", ".wd12"] # Common shards
        self.prefixes = ["", "external-", "careers-"]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
    def check_tenant(self, slug):
        """
         Checks if {slug}.{shard}.myworkdayjobs.com exists.
        """
        for shard in self.shards:
            # Construct candidate domain
            # e.g. netflix.myworkdayjobs.com OR walmart.wd5.myworkdayjobs.com
            candidate_domain = f"{slug}{shard}.{self.base_domain}"
            url = f"https://{candidate_domain}"
            
            try:
                # We use a short timeout.
                r = requests.head(url, headers=self.headers, timeout=3, allow_redirects=True)
                
                # If we get ANY response (even 403, 404, 200), the TENANT exists.
                # If we get ConnectionError (NXDOMAIN), it doesn't exist.
                
                logger.info(f"✅ TENANT FOUND: {slug} ({url})")
                
                # Register
                self.agent.register_endpoint(url + "/common", source="workday_scanner_shard")
                return True
                
            except requests.exceptions.ConnectionError:
                # DNS failure - Tenant does not exist on this shard
                pass
            except Exception as e:
                pass
                
        return False

    def find_career_path(self, base_url, slug):
        """
        Workday usually has paths like /{slug} or /External
        """
        paths = [
            f"/{slug}", 
            "/External", 
            "/Careers", 
            "/w/tm/0/jobs"
        ]
        
        for path in paths:
            full = f"{base_url}{path}"
            try:
                r = requests.head(full, timeout=2)
                if r.status_code == 200:
                    return full
            except: pass
            
        return base_url # Return root if no path found

from us_ats_jobs.intelligence.llm_extractor import LLMService

def generate_fortune_1000():
    llm = LLMService()
    sectors = [
        "Technology", "Finance", "Healthcare", "Retail", "Energy", "Manufacturing",
        "Transportation", "Media", "Construction", "Hospitality", "Automotive",
        "Telecommunications", "Insurance", "Pharmaceuticals", "Aerospace"
    ]
    
    all_slugs = set()
    logger.info("🧠 Brainstorming Fortune 1000 List using Gemini (this takes ~30s)...")
    
    for sector in sectors:
        prompt = f"List 50 major global companies in the sector '{sector}'. Return ONLY the company name per line. Lowercase, no punctuation. Example: 'apple'."
        try:
            text = llm.generate_text(prompt)
            # Regex to remove "1. ", "- ", etc.
            slugs = []
            for line in text.splitlines():
                if not line.strip(): continue
                clean = re.sub(r'^[\d\-\.\s]+', '', line).strip().lower().replace(" ", "")
                if clean: slugs.append(clean)
            
            logger.info(f"   + {sector}: {len(slugs)} companies")
            all_slugs.update(slugs)
        except Exception as e:
            logger.error(f"Error generating {sector}: {e}")
            
    # Add manual giants to be sure
    giants = [
        "amazon", "google", "netflix", "meta", "disney", "apple", "microsoft", 
        "nvidia", "tesla", "spacex", "salesforce", "adobe", "oracle", "ibm",
        "intel", "cisco", "nike", "cocacola", "pepsi", "walmart", "target",
        "homedepot", "costco", "starbucks", "mcdonalds", "visa", "mastercard",
        "amex", "jpmorgan", "goldmansachs", "morganstanley", "pfizer", "moderna",
        "johnsonandjohnson", "pg", "unilever", "nestle", "sony", "samsung",
        "toyota", "honda", "ford", "gm", "boeing", "lockheedmartin"
    ]
    all_slugs.update(giants)
    
    final_list = sorted(list(all_slugs))
    logger.info(f"📋 Generated Target List: {len(final_list)} Unique Companies")
    return final_list

def main():
    scanner = WorkdayScanner()
    
    # Generate List
    targets = generate_fortune_1000()
    
    logger.info(f"🕷️  Spinning up Workday Scanner for {len(targets)} Targets...")
    
    # We use a larger pool for 1000 targets
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        executor.map(scanner.check_tenant, targets)
        
    logger.info("✅ Scan Complete.")

if __name__ == "__main__":
    main()
