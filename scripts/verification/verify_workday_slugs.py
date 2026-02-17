import requests
import json
import random

def fetch_company_jobs_workday(slug):
    """
    slug format: "company|wd#|site_id" e.g. "kohls|wd1|kohlscareers"
    url: https://{company}.wd{num}.myworkdayjobs.com/wday/cxs/{company}/{site_id}/jobs
    """
    try:
        parts = slug.split("|")
        if len(parts) != 3:
            return slug, False, 0, "Invalid Format"

        company, wd, site_id = parts
        wd_num = wd.replace("wd", "")

        base_url = f"https://{company}.wd{wd_num}.myworkdayjobs.com"
        api_url = f"{base_url}/wday/cxs/{company}/{site_id}/jobs"

        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        # Just try to get one page
        payload = {
            "appliedFacets": {},
            "limit": 1,
            "offset": 0,
            "searchText": "",
        }

        response = requests.post(api_url, json=payload, headers=headers, timeout=8)

        # 422 usually means strictly blocked or payload mismatch
        if response.status_code == 422:
             return slug, False, 0, "422 Schema/Block"
        if response.status_code != 200:
             return slug, False, 0, f"HTTP {response.status_code}"

        data = response.json()
        total = data.get("total", 0)
        
        return slug, True, total, "OK"

    except Exception as e:
         return slug, False, 0, str(e)

def main():
    try:
        with open('companies.json', 'r') as f:
            data = json.load(f)
            
        all_workday = data.get('workday', [])
        if not all_workday:
            print("No Workday companies found!")
            return

        print(f"Loaded {len(all_workday)} Workday companies.")
        
        # Shuffle and pick 25
        random.shuffle(all_workday)
        test_batch = all_workday[:25]
        
        print(f"Testing 25 random samples...")
        print("-" * 60)
        
        success_count = 0
        blocked_count = 0
        
        for slug in test_batch:
            slug_str, success, count, msg = fetch_company_jobs_workday(slug)
            status_icon = "✅" if success else "❌"
            if "422" in msg:
                status_icon = "⚠️" 
                blocked_count += 1
            if success:
                success_count += 1
                
            print(f"{status_icon} {slug:<50} | Jobs: {count:<5} | {msg}")
            
        print("-" * 60)
        print(f"Success: {success_count} | 422/Blocked: {blocked_count} | Total Tested: {len(test_batch)}")
        print(f"Success Rate: {(success_count/len(test_batch))*100:.1f}%")

    except Exception as e:
        print(f"Test Failed: {e}")

if __name__ == "__main__":
    main()
