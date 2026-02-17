def normalize_greenhouse(job, company):
    return {
        "job_id": f"greenhouse_{job.get('id')}",
        "title": job.get("title", ""),
        "company": company,
        "location": job.get("location", {}).get("name", ""),
        "job_description": job.get("content", ""),
        "job_link": job.get("absolute_url", ""),
        "source": "greenhouse",
        "date_posted": None
    }



from datetime import datetime

def normalize_lever(job, company):
    ts = job.get("createdAt")

    date_posted = None
    if ts:
        date_posted = datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d")

    return {
        "job_id": f"lever_{job.get('id')}",
        "title": job.get("text", ""),
        "company": company,
        "location": job.get("categories", {}).get("location", ""),
        "job_description": job.get("descriptionPlain", ""),
        "job_link": job.get("hostedUrl", ""),
        "source": "lever",
        "date_posted": date_posted
    }


from datetime import datetime

def normalize_jsearch(job):
    posted_raw = job.get("job_posted_at_datetime_utc")

    date_posted = None
    if posted_raw:
        date_posted = posted_raw[:10]  # YYYY-MM-DD

    return {
        "job_id": f"jsearch_{job.get('job_id')}",
        "title": job.get("job_title", ""),
        "company": job.get("employer_name", ""),
        "location": job.get("job_city", ""),
        "job_description": job.get("job_description", ""),
        "job_link": job.get("job_apply_link", ""),
        "source": "jsearch",
        "date_posted": date_posted
    }


def normalize_linkedin(job):
    return {
        "job_id": f"linkedin_{job.get('job_id') or job.get('id')}",
        "title": job.get("job_title", ""),
        "company": job.get("company_name", ""),
        "location": job.get("job_location", ""),
        "job_description": job.get("job_description", ""),
        "job_link": job.get("job_apply_link", ""),
        "source": "linkedin_rapidapi"
    }


def normalize_ashby(job, company):
    published = job.get("publishedAt")

    date_posted = published[:10] if published else None

    return {
        "job_id": f"ashby_{job.get('id')}",
        "title": job.get("title", ""),
        "company": company,
        "location": job.get("location", ""),
        "job_description": job.get("descriptionHtml", ""),
        "job_link": job.get("applyUrl", ""),
        "source": "ashby",
        "date_posted": date_posted
    }   

def normalize_workable(job, company):
    return {
        "job_id": f"workable_{job.get('shortcode')}",
        "title": job.get("title", ""),
        "company": company,
        "location": job.get("location", {}).get("city", ""),
        "job_description": job.get("description", ""),
        "job_link": job.get("url", ""),
        "source": "workable"
    }

def normalize_usajobs(job):
    descriptor = job.get("MatchedObjectDescriptor", {})
    job_id = descriptor.get("PositionID", "")
    
    # Location usually comes from PositionLocation
    locations = descriptor.get("PositionLocation", [])
    location_str = "Multiple Locations"
    if locations:
        location = locations[0]
        location_str = f"{location.get('LocationName', '')}"

    return {
        "job_id": f"usajobs_{job_id}",
        "title": descriptor.get("PositionTitle", ""),
        "company": descriptor.get("OrganizationName", ""),
        "location": location_str,
        "job_description": descriptor.get("UserArea", {}).get("Details", {}).get("MajorDuties", [""])[0],
        "job_link": descriptor.get("PositionURI", ""),
        "source": "usajobs",
        "date_posted": descriptor.get("PublicationStartDateTime", "")[:10]
    }

def normalize_workday(job, company_name, company_slug):
    # Workday usually returns a relative path like '/job/company/Job-Title_R123'
    link = job.get("externalPath", "")
    
    # Use metadata from fetcher if available (Best for pipe-slugs)
    base_url = job.get("_base_url")
    if base_url:
        full_link = f"{base_url}{link}"
    else:
        # Fallback for old style simple slugs (if any)
        # Try to clean pipe slug if present
        if "|" in company_slug:
             # This is a guess, might be wrong, but better than a pipe URL
             parts = company_slug.split("|")
             clean_sub = f"{parts[0]}.{parts[1]}"
             full_link = f"https://{clean_sub}.myworkdayjobs.com{link}"
        else:
             full_link = f"https://{company_slug}.myworkdayjobs.com{link}"
    
    return {
        "job_id": f"workday_{job.get('bulletinId', job.get('externalPath'))}",
        "title": job.get("title", ""),
        "company": company_name,
        "location": job.get("locationsText", ""),
        "job_description": "", # Workday list API usually doesn't include full description
        "job_link": full_link,
        "source": "workday",
        "date_posted": None
    }

def normalize_bamboohr(job, company):
    """
    Normalizes BambooHR job data to standard format.
    
    BambooHR job structure typically includes:
    - id: Job ID
    - jobOpeningName: Job title
    - location: Location object or string
    - description: Job description
    - applyUrl: Application URL
    """
    # Handle different location formats
    location = ""
    if isinstance(job.get("location"), dict):
        location = job.get("location", {}).get("city", "")
    else:
        location = job.get("location", "")
    
    # BambooHR job ID
    job_id = job.get("id") or job.get("jobOpeningId", "")
    
    # Apply URL
    apply_url = job.get("applyUrl", "")
    if not apply_url:
        # Fallback: construct URL from company subdomain
        company_slug = company.lower().replace(" ", "").replace("-", "")
        apply_url = f"https://{company_slug}.bamboohr.com/jobs/view.php?id={job_id}"
    
    return {
        "job_id": f"bamboohr_{job_id}",
        "title": job.get("jobOpeningName", "") or job.get("title", ""),
        "company": company,
        "location": location,
        "job_description": job.get("description", ""),
        "job_link": apply_url,
        "source": "bamboohr",
        "date_posted": None  # BambooHR doesn't always provide post date in list API
    }

