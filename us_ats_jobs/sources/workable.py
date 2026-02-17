import requests
from us_ats_jobs.utils.crawler_utils import UserAgentRotator

def fetch_workable_jobs(company):
    """
    Fetches jobs from Workable using their public widget API.
    """
    # Clean the company name to create a slug (lowercase, no spaces)
    slug = company.lower().replace(" ", "-").replace(".", "")
    url = f"https://apply.workable.com/api/v1/widget/accounts/{slug}"

    try:
        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": UserAgentRotator.get_random_user_agent(),
                "Accept": "application/json",
                "Referer": f"https://apply.workable.com/{slug}/"
            }
        )
        
        if response.status_code == 404:
            # Try original name if slugging failed
            if slug != company:
                url = f"https://apply.workable.com/api/v1/widget/accounts/{company}"
                response = requests.get(url, timeout=10, headers={"User-Agent": UserAgentRotator.get_random_user_agent()})
            
            if response.status_code == 404:
                raise Exception(f"404 Not Found for {company}")
            
        response.raise_for_status()
        data = response.json()
        return data.get("jobs", [])

    except Exception as e:
        raise Exception(str(e))
