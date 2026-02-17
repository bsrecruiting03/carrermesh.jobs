import requests
import logging
from us_ats_jobs.intelligence.llm_extractor import LLMService

logger = logging.getLogger("UniversalFetcher")

def fetch_universal_jobs(company: str, endpoint_url: str):
    """
    Fetches jobs from any URL by using LLM to parse the HTML.
    """
    if not endpoint_url:
        logger.error("Universal fetcher requires an endpoint_url.")
        return []

    logger.info(f"🤖 Universal Scraper: Fetching {endpoint_url}...")
    
    # 1. Fetch HTML
    # Note: For strict JS sites, we'd need Playwright here. 
    # Fallback to requests for now.
    headers = {
         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    
    try:
        response = requests.get(endpoint_url, headers=headers, timeout=20)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        logger.error(f"❌ Failed to fetch {endpoint_url}: {e}")
        return []
    
    # 2. Extract using LLM
    llm = LLMService()
    if not llm.client:
        logger.warning("LLM Service not available. Universal scraping skipped.")
        return []
        
    try:
        extracted_jobs = llm.extract_job_list(html_content, base_url=endpoint_url)
        logger.info(f"✨ LLM extracted {len(extracted_jobs)} jobs from {company}")
        
        # 3. Normalize to standard list format
        normalized = []
        for job in extracted_jobs:
            normalized.append({
                "job_id": job.url or f"gen-{hash(job.title)}", # Fallback ID
                "company_name": company,
                "title": job.title,
                "job_url": job.url or endpoint_url,
                "location": job.location,
                "department": job.department,
                "description": job.description_snippet
            })
            
        return normalized

    except Exception as e:
        logger.error(f"❌ LLM Parsing failed: {e}")
        return []
