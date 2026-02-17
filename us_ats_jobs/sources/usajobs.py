import requests
import time

def fetch_usajobs_jobs(api_key, email, query="Software Engineer", pages=1):
    """
    Fetches jobs from USAJOBS API.
    Required headers: Host, User-Agent, Authorization-Key.
    """
    if not api_key or not email:
        print("⚠️ USAJOBS_API_KEY or USAJOBS_EMAIL not set. Skipping USAJOBS.")
        return []

    url = "https://data.usajobs.gov/api/Search"
    all_jobs = []
    
    headers = {
        "Host": "data.usajobs.gov",
        "User-Agent": email,
        "Authorization-Key": api_key,
        "Accept": "application/json"
    }

    params = {
        "Keyword": query,
        "ResultsPerPage": 100 # Can go up to 500
    }

    try:
        for page in range(1, pages + 1):
            params["Page"] = page
            print(f"Fetching USAJOBS page {page} for query '{query}'")
            
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 429:
                print("⚠️ USAJOBS Rate Limited - sleeping and skipping remaining pages")
                time.sleep(5)
                break
                
            response.raise_for_status()
            data = response.json()
            
            # The structure is SearchResult -> SearchResultItems
            search_results = data.get("SearchResult", {})
            items = search_results.get("SearchResultItems", [])
            
            if not items:
                break
                
            all_jobs.extend(items)
            
            # Rate limiting check: if results are less than requested per page, we're done
            total_count = search_results.get("SearchResultCountAll", 0)
            if len(all_jobs) >= total_count:
                break

        return all_jobs

    except Exception as e:
        print("⚠️ USAJOBS fetch failed")
        print("Reason:", str(e))
        return []
