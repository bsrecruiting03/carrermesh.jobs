import requests
import time

def fetch_workday_jobs(slug):
    """
    Fetches jobs for a Workday company using the simple API payload.
    Expected slug format: "company|wd#|site_id" e.g. "nvidia|wd5|NvidiaExternalCareerSite"
    """
    try:
        if "|" not in slug:
            print(f"[Workday] Invalid slug format (missing pipes): {slug}")
            return []
            
        parts = slug.split("|")
        if len(parts) < 3:
            print(f"[Workday] Invalid slug structure (need 3 parts): {slug}")
            return []

        # Loose parsing to handle oddities
        company = parts[0]
        wd_raw = parts[1]
        site_id = parts[2]
        
        wd_num = wd_raw.lower().replace("wd", "")

        base_url = f"https://{company}.wd{wd_num}.myworkdayjobs.com"
        api_url = f"{base_url}/wday/cxs/{company}/{site_id}/jobs"

        headers = {
            "Content-Type": "application/json", 
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        all_jobs = []
        offset = 0
        limit = 20

        print(f"   [Workday] Fetching {slug} -> {api_url}")

        while True:
            payload = {
                "appliedFacets": {},
                "limit": limit,
                "offset": offset,
                "searchText": "",
            }

            try:
                response = requests.post(api_url, json=payload, headers=headers, timeout=10)
            except Exception as e:
                print(f"[Workday] Request failed for {slug}: {e}")
                break

            if response.status_code != 200:
                print(f"[Workday] {slug} returned status {response.status_code}")
                # 422 usually means site_id is wrong or headers strictly blocked
                break

            try:
                data = response.json()
            except:
                print(f"[Workday] Failed to parse JSON for {slug}")
                break
                
            postings = data.get("jobPostings", [])
            total = data.get("total", 0)

            if not postings:
                break

            for p in postings:
                # Add metadata to help normalizer
                p["_company_name"] = company
                p["_base_url"] = base_url
                all_jobs.append(p)

            offset += limit
            if offset >= total:
                break
            
            # Simple rate limit protection
            time.sleep(0.2)

        print(f"✅ [Workday] {slug}: Found {len(all_jobs)} jobs")
        return all_jobs

    except Exception as e:
        print(f"[Workday] Error fetching {slug}: {e}")
        return []
