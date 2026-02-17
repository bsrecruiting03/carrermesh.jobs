import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("OracleDebugger")

ORACLE_URL = "https://eeho.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded"
}

def get_count(session, root_url, limit):
    params = {
        "finder": "findReqs",
        "expand": "requisitionList",
        "limit": limit,
        "onlyData": "true" 
    }
    resp = session.get(root_url, params=params)
    if resp.status_code == 200:
        data = resp.json()
        items = data.get('items', [])
        if items:
            root_item = items[0]
            req_list = root_item.get('requisitionList', {})
            if isinstance(req_list, list):
                return len(req_list), "list"
            elif isinstance(req_list, dict):
                 # If it's a dict, it might be {items: [...], count: ...}
                 return len(req_list.get('items', [])), "dict"
    return 0, "unknown"

def main():
    session = requests.Session()
    session.headers.update(HEADERS)
    session.get("https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/jobsearch", timeout=10)
    root_url = "https://eeho.fa.us2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    
    logger.info("Testing Limit=5...")
    c5, t5 = get_count(session, root_url, 5)
    logger.info(f"Count: {c5} (Type: {t5})")
    
    logger.info("Testing Limit=25...")
    c25, t25 = get_count(session, root_url, 25)
    logger.info(f"Count: {c25} (Type: {t25})")
    
    if c25 > c5:
        logger.info("✅ 'limit' param controls expansion size!")
    else:
        logger.info("❌ 'limit' param ignored for expansion.")

if __name__ == "__main__":
    main()
