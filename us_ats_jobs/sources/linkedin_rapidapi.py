import requests

def fetch_linkedin_jobs(
    api_key,
    page=1,
    search_term="software engineer",
    location="United States"
):
    url = "https://real-time-linkedin-job-search-api2.p.rapidapi.com/getjobs"

    payload = {
        "search_term": search_term,
        "location": location,
        "results_wanted": 20,
        "site_name": ["linkedin"],
        "distance": 50,
        "job_type": "fulltime",
        "is_remote": False,
        "linkedin_fetch_description": True,
        "hours_old": 24,
        "page": page
    }

    headers = {
        "Content-Type": "application/json",
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "real-time-linkedin-job-search-api2.p.rapidapi.com"
    }

    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=20
    )
    response.raise_for_status()

    return response.json().get("data", [])
