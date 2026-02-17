import requests
import re

def fetch_greenhouse_jobs(company, endpoint_url=None):
    """
    Fetches jobs from Greenhouse.
    Args:
        company: The slug or company name (legacy).
        endpoint_url: The full URL (e.g. https://boards.greenhouse.io/stripe).
    """
    slug = company
    
    # Try to extract better slug from URL
    if endpoint_url:
        # Matches boards.greenhouse.io/SLUG or boards-api.greenhouse.io/v1/boards/SLUG
        # We want the first path segment usually
        try:
            # simple heuristic: remove protocol, split by /
            clean = endpoint_url.replace("https://", "").replace("http://", "")
            parts = clean.split("/")
            
            if "boards-api" in parts[0]:
                # .../v1/boards/SLUG/...
                if len(parts) > 3: slug = parts[3]
            else:
                # boards.greenhouse.io/SLUG
                if len(parts) > 1 and parts[1]: 
                    slug = parts[1]
                    # if slug is 'embed', ignore? Greenhouse doesn't usually use embed path for main board
        except:
            pass

    # Construct API URL
    # API: https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
    # We must ensure we don't use "jobs" as the slug if the URL was .../stripe/jobs
    if slug == "jobs":
         # Fallback logic failed or URL was weird.
         # Try to recover if endpoint_url exists
         if endpoint_url and "jobs" in endpoint_url:
             pass 

    api_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"

    try:
        response = requests.get(
            api_url,
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }
        )
        response.raise_for_status()
        return response.json().get("jobs", [])

    except requests.exceptions.RequestException as e:
        # Silent fail for now or log
        # print(f"⚠️ Greenhouse failed for {slug} — skipping")
        return []

