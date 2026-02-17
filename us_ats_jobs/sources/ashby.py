import requests

def fetch_ashby_jobs(company, endpoint_url=None):
    slug = company
    if endpoint_url:
        try:
            clean = endpoint_url.replace("https://", "").replace("http://", "")
            parts = clean.split("/")
             # jobs.ashbyhq.com/SLUG
            if len(parts) > 1 and parts[1]:
                slug = parts[1]
        except: pass

    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"

    try:
        response = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()
        return response.json().get("jobs", [])

    except:
        return []

    