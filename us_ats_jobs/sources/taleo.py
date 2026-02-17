"""
Taleo ATS Adapter

Oracle Taleo (used by Oracle, JPMorgan, Goldman Sachs, Ford, etc.)
supports several integration patterns:

1. Oracle HCM Cloud (modern) - REST API at /hcmRestApi/resources/
2. Taleo Enterprise (legacy) - Career sections with /careersection/
3. Taleo Business Edition - Simpler API structure

This adapter supports the most common pattern: Career Section REST endpoints.
"""

import requests
import time
import re
import json
from urllib.parse import urlparse, urljoin

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_taleo_jobs(company, endpoint_url=None):
    """
    Fetches jobs from Oracle Taleo career sections.
    
    Args:
        company: Company slug (e.g., 'oracle', 'jpmorgan')
        endpoint_url: Full Taleo URL (e.g., 'https://oracle.taleo.net/careersection/2/jobsearch.ftl')
    
    Returns:
        List of job dictionaries
    """
    if not endpoint_url:
        # Try to construct common Taleo URL patterns
        endpoint_url = f"https://{company}.taleo.net/careersection/2/jobsearch.ftl"
    
    print(f"   [Taleo] Fetching {company} -> {endpoint_url}")
    
    # Determine the Taleo instance type and use appropriate method
    parsed = urlparse(endpoint_url)
    
    # Try modern Oracle HCM Cloud REST API first
    if 'oraclecloud.com' in parsed.netloc:
        return _fetch_oracle_hcm(company, endpoint_url)
    
    # Standard Taleo Enterprise
    return _fetch_taleo_enterprise(company, endpoint_url)


def _fetch_taleo_enterprise(company: str, base_url: str) -> list:
    """
    Fetch from standard Taleo Enterprise career sections.
    Taleo uses a session-based system with AJAX endpoints.
    """
    all_jobs = []
    
    try:
        parsed = urlparse(base_url)
        base_host = f"{parsed.scheme}://{parsed.netloc}"
        
        # Extract career section ID from URL
        # Pattern: /careersection/{id}/... 
        cs_match = re.search(r'/careersection/(\d+|[\w-]+)/', base_url)
        career_section = cs_match.group(1) if cs_match else "2"
        
        # Taleo AJAX search endpoint
        # Pattern: /careersection/{id}/moresearch.ftl or /careersection/{id}/searchjobresults.ftl
        search_url = f"{base_host}/careersection/{career_section}/moresearch.ftl"
        
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Step 1: Visit main page to get session/CSRF tokens
        try:
            init_resp = session.get(base_url, timeout=15)
            init_resp.raise_for_status()
            
            # Check if redirect to login or blocked
            if 'login' in init_resp.url.lower() or init_resp.status_code == 403:
                print(f"  ⚠️ [Taleo] {company}: Blocked or requires login")
                return []
                
        except requests.exceptions.RequestException as e:
            print(f"  ⚠️ [Taleo] {company}: Init failed - {e}")
            return []
        
        # Step 2: Try JSON search endpoint
        # Modern Taleo has JSON endpoints at /careersection/rest/
        rest_url = f"{base_host}/careersection/rest/{career_section}/jobs"
        
        try:
            rest_resp = session.get(
                rest_url,
                params={"limit": 100, "offset": 0},
                timeout=15
            )
            
            if rest_resp.status_code == 200:
                data = rest_resp.json()
                if isinstance(data, list):
                    all_jobs = data
                elif isinstance(data, dict):
                    all_jobs = data.get('jobs', data.get('requisitions', []))
                    
                if all_jobs:
                    print(f"✅ [Taleo] {company}: Found {len(all_jobs)} jobs via REST")
                    return _normalize_taleo_jobs(all_jobs, company, base_host)
                    
        except (requests.exceptions.RequestException, json.JSONDecodeError):
            pass  # Fall through to HTML parsing
        
        # Step 3: Fallback to HTML parsing
        all_jobs = _parse_taleo_html(session, base_url, company)
        
    except Exception as e:
        print(f"  ❌ [Taleo] {company}: Error - {e}")
    
    return all_jobs


def _fetch_oracle_hcm(company: str, base_url: str) -> list:
    """
    Fetch from Oracle HCM Cloud (modern cloud-based system).
    Uses REST API at /hcmRestApi/resources/latest/recruitingCEJobRequisitions
    """
    all_jobs = []
    
    try:
        parsed = urlparse(base_url)
        base_host = f"{parsed.scheme}://{parsed.netloc}"
        
        # Oracle HCM REST endpoint
        api_url = f"{base_host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
        
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Visit HTML first to establish cookies
        try:
            html_url = f"{base_host}/hcmUI/CandidateExperience/en/sites/jobsearch"
            session.get(html_url, timeout=10)
        except Exception:
            pass
        
        # Fetch with expansion
        # Note: Pagination via offset is flaky for expanded resources, so we use a high limit
        params = {
            "finder": "findReqs",
            "expand": "requisitionList",
            "onlyData": "true",
            "limit": 499  # Max safe limit for most Oracle instances
        }
            
        try:
            resp = session.get(api_url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            
            items = data.get('items', [])
            if items:
                root_item = items[0]
                # Extract expanded jobs
                req_list = root_item.get('requisitionList', {})
                if isinstance(req_list, list):
                    all_jobs = req_list
                else:
                    all_jobs = req_list.get('items', [])
            
        except Exception as e:
            print(f"  ⚠️ [Taleo HCM] {company}: Fetch failed - {e}")
        
        print(f"✅ [Taleo HCM] {company}: Found {len(all_jobs)} jobs")
        return _normalize_hcm_jobs(all_jobs, company, base_host)
        
    except Exception as e:
        print(f"  ❌ [Taleo HCM] {company}: Error - {e}")
    
    return all_jobs


def _parse_taleo_html(session: requests.Session, url: str, company: str) -> list:
    """
    Parse job listings from Taleo HTML pages.
    Fallback when REST endpoints are not available.
    """
    all_jobs = []
    
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        html = resp.text
        
        # Parse job links from HTML
        # Pattern: /careersection/{id}/jobdetail.ftl?job={job_id}
        job_pattern = re.compile(
            r'jobdetail\.ftl\?job=([^"&\s]+)',
            re.IGNORECASE
        )
        
        # Find job IDs
        job_ids = set(job_pattern.findall(html))
        
        # Also try to find job titles and other metadata from table rows
        # Taleo typically uses table-based layouts
        title_pattern = re.compile(
            r'class="[^"]*jobTitle[^"]*"[^>]*>([^<]+)</a?>',
            re.IGNORECASE
        )
        
        titles = title_pattern.findall(html)
        
        # Build basic job objects from what we found
        parsed = urlparse(url)
        base_host = f"{parsed.scheme}://{parsed.netloc}"
        
        for i, job_id in enumerate(job_ids):
            job = {
                'id': job_id,
                'external_id': job_id,
                'title': titles[i] if i < len(titles) else f"Position {job_id}",
                'url': f"{base_host}/careersection/2/jobdetail.ftl?job={job_id}",
                '_company_name': company,
                '_source': 'taleo_html'
            }
            all_jobs.append(job)
        
        if all_jobs:
            print(f"✅ [Taleo HTML] {company}: Found {len(all_jobs)} jobs")
        else:
            print(f"  ⚠️ [Taleo HTML] {company}: No jobs found in HTML")
            
    except Exception as e:
        print(f"  ❌ [Taleo HTML] {company}: Parse error - {e}")
    
    return all_jobs


def _normalize_taleo_jobs(jobs: list, company: str, base_url: str) -> list:
    """Normalize Taleo REST API response to standard format."""
    normalized = []
    
    for job in jobs:
        try:
            normalized.append({
                'id': job.get('id') or job.get('requisitionId') or job.get('jobId'),
                'external_id': job.get('requisitionNumber') or job.get('id'),
                'title': job.get('title') or job.get('jobTitle') or job.get('name'),
                'location': job.get('location') or job.get('primaryLocation', {}).get('name'),
                'department': job.get('organization') or job.get('department'),
                'description': job.get('description') or job.get('jobDescription'),
                'url': job.get('applyUrl') or f"{base_url}/careersection/2/jobdetail.ftl?job={job.get('id')}",
                'posted_date': job.get('postingDate') or job.get('datePosted'),
                '_company_name': company,
                '_source': 'taleo_rest',
                '_raw': job
            })
        except Exception:
            continue
    
    return normalized


def _normalize_hcm_jobs(jobs: list, company: str, base_url: str) -> list:
    """Normalize Oracle HCM Cloud response to standard format."""
    normalized = []
    
    for job in jobs:
        try:
            normalized.append({
                'id': job.get('RequisitionId') or job.get('Id'),
                'external_id': job.get('RequisitionNumber'),
                'title': job.get('Title') or job.get('RequisitionTitle'),
                'location': job.get('PrimaryWorkLocation'),
                'department': job.get('Organization') or job.get('BusinessUnit'),
                'description': job.get('ShortDescription') or job.get('Description'),
                'url': job.get('ApplyUrl') or f"{base_url}/hcmUI/CandidateExperience",
                'posted_date': job.get('PostedDate'),
                '_company_name': company,
                '_source': 'oracle_hcm',
                '_raw': job
            })
        except Exception:
            continue
    
    return normalized


# =============================================================================
# KNOWN TALEO ENDPOINTS (Company-specific configurations)
# =============================================================================

KNOWN_TALEO_CONFIGS = {
    "oracle": {
        # Oracle uses Oracle HCM Cloud (their own product)
        "url": "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/jobsearch",
        "type": "hcm_cloud"
    },
    "jpmorgan": {
        # JPMorgan uses Oracle HCM Cloud
        "url": "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001",
        "type": "hcm_cloud"
    },
    "goldmansachs": {
        # Goldman Sachs uses custom portal
        "url": "https://www.goldmansachs.com/careers/find-a-job",
        "type": "custom"  # Needs custom scraper, not Taleo
    },
    "ford": {
        # Ford uses Oracle HCM Cloud
        "url": "https://efds.fa.us6.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1",
        "type": "hcm_cloud"
    },
}


def fetch_taleo_jobs_with_config(company: str) -> list:
    """
    Fetch jobs using known company-specific configurations.
    """
    config = KNOWN_TALEO_CONFIGS.get(company.lower())
    
    if not config:
        print(f"  ⚠️ [Taleo] No config for {company}")
        return []
    
    endpoint_type = config.get('type', 'enterprise')
    url = config['url']
    
    if endpoint_type == 'hcm_cloud':
        return _fetch_oracle_hcm(company, url)
    elif endpoint_type == 'talentlink':
        return _fetch_talentlink(company, url)
    else:
        return _fetch_taleo_enterprise(company, url)


def _fetch_talentlink(company: str, url: str) -> list:
    """
    Fetch from Taleo Talent Link (used by Goldman Sachs, etc.)
    Uses different API structure.
    """
    all_jobs = []
    
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Talent Link API endpoint
        parsed = urlparse(url)
        base_host = f"{parsed.scheme}://{parsed.netloc}"
        
        # Try JSON API
        api_url = f"{base_host}/vx/mobile-0/appcentre-1/brand-2/candidate/jobboard/vacancy/list"
        
        try:
            resp = session.get(api_url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                jobs = data.get('vacancies', data.get('jobs', []))
                
                for job in jobs:
                    all_jobs.append({
                        'id': job.get('id') or job.get('vacancyId'),
                        'external_id': job.get('refNo') or job.get('id'),
                        'title': job.get('title') or job.get('jobTitle'),
                        'location': job.get('location'),
                        'department': job.get('division'),
                        'url': job.get('applyUrl') or f"{base_host}/vx/candidate/job/{job.get('id')}",
                        '_company_name': company,
                        '_source': 'talentlink'
                    })
                    
                print(f"✅ [TalentLink] {company}: Found {len(all_jobs)} jobs")
                
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            print(f"  ⚠️ [TalentLink] {company}: API failed - {e}")
            
    except Exception as e:
        print(f"  ❌ [TalentLink] {company}: Error - {e}")
    
    return all_jobs


if __name__ == "__main__":
    # Test the adapter
    import sys
    
    company = sys.argv[1] if len(sys.argv) > 1 else "oracle"
    
    print(f"\n🧪 Testing Taleo adapter for: {company}")
    print("=" * 50)
    
    jobs = fetch_taleo_jobs_with_config(company)
    
    print(f"\n📊 Results: {len(jobs)} jobs found")
    for job in jobs[:5]:
        print(f"  - {job.get('title', 'No title')}")
