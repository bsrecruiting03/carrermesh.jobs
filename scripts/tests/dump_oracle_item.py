import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OracleDumper")

ORACLE_URL = "https://eeho.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json",
}

def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    
    # Visit HTML
    session.get("https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/jobsearch", timeout=10)
    
    # Hit API
    params = {
        "onlyData": "true",
        "limit": 5,
        "finder": "findReqs"
    }
    
    resp = session.get(ORACLE_URL, params=params, timeout=15)
    logger.info(f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        with open("oracle_debug.json", "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Saved to oracle_debug.json")
        
        items = data.get('items', [])
        logger.info(f"Items found: {len(items)}")
        if items:
            logger.info(f"Item 0 Keys: {list(items[0].keys())}")

if __name__ == "__main__":
    main()
