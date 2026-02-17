import os
import sys
import requests
import logging
from concurrent.futures import ThreadPoolExecutor

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.discovery.main import DiscoveryAgent
from us_ats_jobs.intelligence.llm_extractor import LLMService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BruteForceDiscovery")

COMMON_SLUGS = [
    "stripe", "airbnb", "uber", "lyft", "coinbase", "flexport", "plaid", 
    "dropbox", "slack", "square", "block", "cashapp", "robinhood", "chime",
    "brex", "ramp", "gusto", "notion", "figma", "canva", "miro", "loom",
    "zapier", "webflow", "airtable", "monday", "clickup", "asana", "linear",
    "coda", "retool", "vercel", "netlify", "heroku", "digitalocean",
    "docker", "kubernetes", "hashicorp", "confluent", "databricks", "snowflake",
    "mongodb", "elastic", "redis", "neo4j", "cockroachlabs", "yugabyte",
    "timescale", "scylladb", "planetscale", "neon", "supabase", "firebase",
    "auth0", "okta", "onelogin", "pingidentity", "cyberark", "crowdstrike",
    "sentinelone", "paloaltonetworks", "zscaler", "cloudflare", "fastly",
    "akamai", "nginx", "f5", "cisco", "juniper", "arista", "ubiquiti",
    "nvidia", "amd", "intel", "qualcomm", "broadcom", "tsmc", "asml",
    "samsung", "lg", "sony", "panasonic", "toshiba", "sharp", "canon",
    "nikon", "fujifilm", "olympus", "leica", "hasselblad", "red", "arri",
    "blackmagic", "gopro", "dji", "insta360", "parrot", "skydio", "anduril"
]
# In a real run, load 10k names from a file

TARGETS = [
    "https://boards.greenhouse.io/{}",
    "https://jobs.lever.co/{}",
    "https://jobs.ashbyhq.com/{}",
    "https://{}.bamboohr.com/careers"
]

def check_slug(slug):
    agent = DiscoveryAgent() # Connects each thread? Better to pass it.
    # Actually, let's just print/collect, then register active ones to avoid DB lock spam in threads.
    
    found = []
    
    for template in TARGETS:
        url = template.format(slug)
        try:
            r = requests.head(url, timeout=3)
            # Greenhouse redirects to /embed/ sometimes, but usually 200 or 301 is good.
            # 404 is bad.
            if r.status_code == 200:
                logger.info(f"✅ FOUND: {url}")
                found.append(url)
            elif r.status_code == 301 or r.status_code == 302:
                # Follow redirect?
                if "greenhouse.io" in url: # Greenhouse often redirects
                     found.append(url)
        except:
            pass
            
    return found

def auto_discovery():
    """
    Asks LLM for lists of companies and checks them.
    """
    llm = LLMService()
    sectors = [
        "Top 50 SaaS Companies",
        "Top 50 AI Startups 2024",
        "Top 50 Fintech Companies",
        "Top 50 Biotech Companies",
        "Top 50 Ecommerce Brands",
        "Top 50 Cybersecurity Companies",
        "Top 50 Remote-First Companies"
    ]
    
    all_slugs = set()
    
    for sector in sectors:
        logger.info(f"🧠 Brainstorming: {sector}...")
        prompt = f"""listing 50 companies in the sector: '{sector}'.
        Return ONLY a list of their names as simple lowercase slugs (e.g. 'stripe', 'airbnb').
        Do not include numbers or bullets. Just the names, one per line.
        """
        text = llm.generate_text(prompt)
        if not text: continue
        
        # Parse
        lines = text.strip().split('\n')
        for line in lines:
            slug = line.strip().lower().replace(' ', '').replace('.', '')
            if len(slug) > 2:
                all_slugs.add(slug)
                
    return list(all_slugs)

def main():
    agent = DiscoveryAgent()
    total_found = 0
    
    # Check if we should use Auto Mode
    slugs_to_check = []
    
    # Always mix in common slugs + new LLM ones
    slugs_to_check.extend(COMMON_SLUGS)
    
    # Auto Generate
    logger.info("🤖 Generating company lists via Gemini...")
    generated = auto_discovery()
    slugs_to_check.extend(generated)
    
    # Deduplicate
    slugs_to_check = sorted(list(set(slugs_to_check)))
    
    logger.info(f"🚀 Starting Brute Force Discovery on {len(slugs_to_check)} unique slugs...")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(check_slug, slugs_to_check)
        
        for batch in results:
            for url in batch:
                if agent.register_endpoint(url, source="brute_force_llm"):
                    total_found += 1
                    
    logger.info(f"🏁 Discovery Complete. Registered {total_found} new endpoints.")
    agent.close()

if __name__ == "__main__":
    main()
