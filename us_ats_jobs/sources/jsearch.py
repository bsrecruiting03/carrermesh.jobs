import requests

def fetch_jsearch_jobs(api_key, page=1, query="software engineer"):
    url = "https://jsearch.p.rapidapi.com/search"

    params = {
        "query": query,
        "page": page,
        "num_pages": 1,
        "country": "us"
    }

    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=15
    )
    response.raise_for_status()

    print("DEBUG HEADERS:", headers)

    return response.json().get("data", [])
