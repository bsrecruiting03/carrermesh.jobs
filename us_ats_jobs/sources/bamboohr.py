import requests
from us_ats_jobs.utils.crawler_utils import UserAgentRotator

def fetch_bamboohr_jobs(company):
    """
    Fetches jobs from BambooHR using their public jobs API.
    
    Args:
        company: Company subdomain (e.g., 'example' for example.bamboohr.com)
    
    Returns:
        List of job listings
    """
    # BambooHR uses subdomain-based URLs
    # Example: https://example.bamboohr.com/careers/
    
    slug = company.lower().replace(" ", "").replace("-", "")
    
    # BambooHR jobs endpoint (FIXED: changed from /jobs/list to /careers/list)
    url = f"https://{slug}.bamboohr.com/careers/list"
    
    try:
        headers = {
            "User-Agent": UserAgentRotator.get_random_user_agent(),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://{slug}.bamboohr.com/jobs/"
        }
        
        response = requests.get(
            url,
            timeout=15,
            headers=headers
        )
        
        if response.status_code == 404:
            raise Exception(f"404 Not Found for {company}")
        
        response.raise_for_status()
        
        # BambooHR returns JSON with a 'result' field containing job listings
        data = response.json()
        
        # Handle different response formats
        if isinstance(data, dict):
            return data.get("result", data.get("jobs", []))
        elif isinstance(data, list):
            return data
        else:
            return []
    
    except Exception as e:
        raise Exception(str(e))
