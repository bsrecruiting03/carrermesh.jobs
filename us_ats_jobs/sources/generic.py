import requests
from bs4 import BeautifulSoup
import json
import logging
import extruct
from w3lib.html import get_base_url
import xml.etree.ElementTree as ET
import gzip
import io

logger = logging.getLogger("Worker.Generic")

def fetch_sitemap_jobs(company_name, base_url):
    """
    Attempts to find and parse a sitemap.xml for job links.
    Handles standard sitemap and sitemap index.
    """
    try:
        from urllib.parse import urlparse, urljoin
        parsed = urlparse(base_url)
        # diverse attempts
        candidates = [
            f"{parsed.scheme}://{parsed.netloc}/sitemap.xml",
            f"{parsed.scheme}://{parsed.netloc}/careers/sitemap.xml",
            urljoin(base_url, "sitemap.xml")
        ]
        # Deduplicate
        candidates = list(set(candidates))
        
        jobs = []
        found_sitemap = False

        for sitemap_url in candidates:
            try:
                resp = requests.get(sitemap_url, timeout=10, stream=True)
                if resp.status_code != 200: continue
                
                content = resp.content
                # Handle gzip
                if sitemap_url.endswith('.gz'):
                    try:
                        with gzip.GzipFile(fileobj=io.BytesIO(content)) as f:
                            content = f.read()
                    except: pass
                
                try:
                    root = ET.fromstring(content)
                except:
                    continue # Not valid XML

                # Check if it's a standard urlset or sitemapindex
                # Namespaces can be annoying in ET, so we might ignore them or handle loosely
                # Simple heuristic: scan all 'loc' tags
                
                found_links = 0
                for elem in root.iter():
                    if 'loc' in elem.tag:
                        url = elem.text.strip()
                        if not url: continue
                        
                        # Filter: Must look like a job
                        # (Many sitemaps have every static page, we want jobs)
                        if any(k in url.lower() for k in ["/job/", "/role/", "/position/", "/career/", "/openings/"]):
                             # Avoid the indices themselves
                             if "sitemap" in url.lower(): continue 
                             
                             jobs.append({
                                 "@type": "JobPosting", 
                                 "title": "Detected from Sitemap", # We don't have title often in simple sitemaps
                                 "url": url,
                                 "description": "via Sitemap.xml"
                             })
                             found_links += 1
                
                if found_links > 0:
                    logger.info(f"🗺️  Found Sitemap at {sitemap_url} with {found_links} potential jobs.")
                    found_sitemap = True
                    break # Stop after finding a working one

            except Exception as e:
                logger.debug(f"Sitemap check failed for {sitemap_url}: {e}")
        
        return jobs

    except Exception as e:
        logger.warning(f"Sitemap strategy error: {e}")
        return []

def fetch_generic_jobs(company_name, career_page_url):
    """
    Fetches jobs from a generic career page using:
    1. Schema.org (JSON-LD) extraction (Best)
    2. Sitemap.xml discovery (Safe/Efficient)
    3. Heuristic Link Scanning (Fallback)
    """
    if not career_page_url:
        logger.warning(f"⚠️ No Career URL for {company_name}")
        return []

    logger.info(f"🌐 Fetching Generic: {company_name} -> {career_page_url}")

    # 1. Try Schema.org first (Pages often load this dynamic or static)
    try:
        response = requests.get(
            career_page_url, 
            timeout=20, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        response.raise_for_status()
        
        base_url = get_base_url(response.text, response.url)
        data = extruct.extract(response.text, base_url=base_url, syntaxes=['json-ld'])
        
        jobs = []
        json_ld_items = data.get("json-ld", [])
        
        flattened_items = []
        for item in json_ld_items:
            if isinstance(item, list): flattened_items.extend(item)
            elif item.get("@graph"): flattened_items.extend(item["@graph"])
            else: flattened_items.append(item)

        for item in flattened_items:
            itype = item.get("@type")
            if isinstance(itype, list):
                if "JobPosting" in itype: jobs.append(item)
            elif itype == "JobPosting":
                 jobs.append(item)

        if jobs:
            logger.info(f"✨ Found {len(jobs)} Schema.org jobs for {company_name}")
            return jobs

    except Exception as e:
        logger.error(f"❌ Schema fetch failed for {company_name}: {e}")
        # Don't return empty yet, try other strategies

    # 2. Strategy: Sitemap.xml
    logger.info("Checking Sitemaps...")
    sitemap_jobs = fetch_sitemap_jobs(company_name, career_page_url)
    if sitemap_jobs:
        logger.info(f"✨ Found {len(sitemap_jobs)} jobs via Sitemap.")
        return sitemap_jobs

    # 3. Fallback: Heuristic Link Scraper (HTML Scan)
    logger.info(f"⚠️ No Schema/Sitemap. Falling back to Link Scanning...")
    try:
        # Re-use response if we have it, else fetch
        if 'response' not in locals():
             response = requests.get(career_page_url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        seen_links = set()
        jobs = []
        base_url = response.url # accurate base
        
        for a in soup.find_all("a", href=True):
            href = a['href']
            if any(k in href.lower() for k in ["/job/", "/role/", "/position/", "/career/"]):
                 full_url = requests.compat.urljoin(base_url, href)
                 if full_url not in seen_links:
                     seen_links.add(full_url)
                     jobs.append({
                         "@type": "JobPosting",
                         "title": a.get_text(strip=True) or "Unknown Role",
                         "url": full_url,
                         "description": "Detected via link scan"
                     })
        
        logger.info(f"🔍 Found {len(jobs)} potential job links via scanning.")
        return jobs
    except Exception as e:
         logger.error(f"Link scan failed: {e}")
         return []

def normalize_generic(job, company_name):
    """
    Normalizes a Schema.org or Sitemap JobPosting dict to our internal structure.
    """
    
    def parse_location(loc_obj):
        if not loc_obj: return "Remote"
        if isinstance(loc_obj, str): return loc_obj
        if isinstance(loc_obj, dict):
            addr = loc_obj.get("address", {})
            if isinstance(addr, dict):
                parts = [
                    addr.get("addressLocality"), 
                    addr.get("addressRegion"), 
                    addr.get("addressCountry")
                ]
                return ", ".join([p for p in parts if p])
            elif isinstance(addr, str):
                return addr
        return "Unknown"

    return {
        "job_id": job.get("identifier", {}).get("value") or job.get("url") or str(hash(job.get("description", ""))),
        "title": job.get("title", "Unknown Role"),
        "company": company_name,
        "location": parse_location(job.get("jobLocation")),
        "job_description": job.get("description", ""),
        "job_link": job.get("url", ""),
        "source": "generic",
        "date_posted": job.get("datePosted"),
        "work_mode": job.get("jobLocationType", None) 
    }
    """
    Fetches jobs from a generic career page using Schema.org (JSON-LD) extraction.
    Falls back to heuristic link scanning if no structured data found.
    """
    if not career_page_url:
        logger.warning(f"⚠️ No Career URL for {company_name}")
        return []

    logger.info(f"🌐 Fetching Generic: {company_name} -> {career_page_url}")

    try:
        response = requests.get(
            career_page_url, 
            timeout=20, 
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        response.raise_for_status()
        
        # 1. Try Schema.org first
        base_url = get_base_url(response.text, response.url)
        data = extruct.extract(response.text, base_url=base_url, syntaxes=['json-ld'])
        
        jobs = []
        json_ld_items = data.get("json-ld", [])
        
        # Flatten and Filter (Code omitted for brevity, same as before)
        flattened_items = []
        for item in json_ld_items:
            if isinstance(item, list): flattened_items.extend(item)
            elif item.get("@graph"): flattened_items.extend(item["@graph"])
            else: flattened_items.append(item)

        for item in flattened_items:
            itype = item.get("@type")
            if isinstance(itype, list):
                if "JobPosting" in itype: jobs.append(item)
            elif itype == "JobPosting":
                 jobs.append(item)

        if jobs:
            logger.info(f"✨ Found {len(jobs)} Schema.org jobs for {company_name}")
            return jobs

        # 2. Fallback: Heuristic Link Scraper
        logger.info(f"⚠️ No Schema.org data. Falling back to Link Scanning...")
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find all links that look like jobs
        seen_links = set()
        for a in soup.find_all("a", href=True):
            href = a['href']
            # Heuristic: URL contains /job/ or /careers/ and title/text indicates a role
            if any(k in href.lower() for k in ["/job/", "/role/", "/position/", "/career/"]):
                 full_url = requests.compat.urljoin(base_url, href)
                 if full_url not in seen_links:
                     seen_links.add(full_url)
                     jobs.append({
                         "@type": "JobPosting", # Mock type for normalizer
                         "title": a.get_text(strip=True) or "Unknown Role",
                         "url": full_url,
                         "description": "Detected via link scan"
                     })
        
        logger.info(f"🔍 Found {len(jobs)} potential job links via scanning.")
        return jobs

    except Exception as e:
        logger.error(f"❌ Generic fetch failed for {company_name}: {e}")
        return []

def normalize_generic(job, company_name):
    """
    Normalizes a Schema.org JobPosting dict to our internal structure.
    """
    
    # helper for nested location
    def parse_location(loc_obj):
        if not loc_obj: return "Remote"
        if isinstance(loc_obj, str): return loc_obj
        if isinstance(loc_obj, dict):
            # Try address
            addr = loc_obj.get("address", {})
            if isinstance(addr, dict):
                parts = [
                    addr.get("addressLocality"), 
                    addr.get("addressRegion"), 
                    addr.get("addressCountry")
                ]
                return ", ".join([p for p in parts if p])
            elif isinstance(addr, str):
                return addr
        return "Unknown"

    return {
        "job_id": job.get("identifier", {}).get("value") or job.get("url") or str(hash(job.get("description", ""))),
        "title": job.get("title", "Unknown Role"),
        "company": company_name,
        "location": parse_location(job.get("jobLocation")),
        "job_description": job.get("description", ""),
        "job_link": job.get("url", ""),
        "source": "generic",
        "date_posted": job.get("datePosted"),
        "work_mode": job.get("jobLocationType", None) # e.g. TELECOMMUTE
    }
