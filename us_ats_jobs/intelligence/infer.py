import re
from datetime import date, datetime

# Import new enrichment modules
# Import new enrichment modules
from us_ats_jobs.intelligence.skills import extract_tech_stack
from us_ats_jobs.intelligence.qualifications import extract_qualifications
from us_ats_jobs.intelligence.summarizer import generate_noise_free_summary

# ---------- work mode detection ----------
REMOTE_KWS = ["remote", "work from home", "work-from-home", "wfh", "anywhere", "telecommute"]
HYBRID_KWS = ["hybrid", "flexible", "partial remote"]
ONSITE_KWS = ["onsite", "on-site", "in-office", "office-based"]

def infer_work_mode(location: str, description: str) -> str:
    """
    Categorizes work into 'remote', 'hybrid', or 'onsite'.
    """
    text = " ".join(filter(None, [location, description])).lower()
    
    # Priority 1: Hybrid (most specific)
    for kw in HYBRID_KWS:
        if kw in text:
            return "hybrid"
            
    # Priority 2: Remote
    for kw in REMOTE_KWS:
        if kw in text:
            return "remote"
            
    # Priority 3: Onsite keywords
    for kw in ONSITE_KWS:
        if kw in text:
            return "onsite"
            
    # Default: Onsite (if nothing else mentioned)
    return "onsite"

# ---------- seniority ----------
SENIOR_PATTERNS = [
    (r"\b(senior|sr\.|sr |staff|principal|lead)\b", "senior"),
    (r"\b(junior|jr\.|jr |intern|trainee)\b", "junior"),
    (r"\b(mid|mid-level|associate)\b", "mid"),
]

def infer_seniority(title: str, description: str = "") -> str:
    t = (title or "").lower()
    d = (description or "").lower()
    for pat, label in SENIOR_PATTERNS:
        if re.search(pat, t) or re.search(pat, d):
            return label
    return "mid"  # safe default

# ---------- department ----------
DEPT_MAP = {
    "engineering": ["engineer", "developer", "software", "backend", "frontend", "full[- ]?stack"],
    "data": ["data scientist", "data engineer", "ml", "machine learning", "analytics"],
    "product": ["product manager", r"\bpm\b"],
    "design": ["designer", "ux", "ui", "product designer"],
    "sales": ["account executive", "sales", "business development", "bdm"],
}

def infer_department(title: str, description: str = "") -> str:
    text = " ".join([title or "", description or ""]).lower()
    for dept, kws in DEPT_MAP.items():
        for kw in kws:
            if re.search(kw, text):
                return dept
    return "other"

# ---------- bucket posted ----------
def bucket_posted(date_posted_str):
    """
    Returns 'last_24h', 'last_7d', 'last_30d', or 'older'.
    Expects date_posted_str in 'YYYY-MM-DD' format.
    """
    if not date_posted_str:
        return "unknown"

    try:
        # Handle cases where date_posted might be a full datetime string
        if "T" in date_posted_str:
             date_posted_str = date_posted_str.split("T")[0]
             
        posted_date = datetime.strptime(date_posted_str, "%Y-%m-%d").date()
        today = date.today()
        # Handle future dates or timezone diffs (if any)
        delta = today - posted_date

        if delta.days <= 1:
            return "last_24h"
        if delta.days <= 7:
            return "last_7d"
        if delta.days <= 30:
            return "last_30d"
        return "older"
    except Exception as e:
        return "unknown"

# ---------- salary extraction (best-effort) ----------
# Handles: "$120k", "120,000 USD", "£40k", "120000 - 150000", "120k-150k", "€50,000 per year"
SAL_REGEXPS = [
    # USD 120k or 120K
    # Added negative lookahead to avoid "$4.5 billion"
    r"(?P<prefix>[$€£])\s?(?P<low>\d{1,3}(?:[,.\d]*))(?:k\b|K\b)?(?:\s*-\s*(?P<high>\d{1,3}(?:[,.\d]*))(?:k\b|K\b)?)?(?!\s*(?:trillion|billion|million|b\b|m\b))",
    # number ranges with currency code or no symbol
    r"(?P<low>\d{2,3}[,.\d]{0,3})(?:\s*(?:-|to)\s*)(?P<high>\d{2,3}[,.\d]{0,3})\s*(?P<curr>USD|EUR|GBP|\$|€|£)?",
    # 120000 USD
    r"(?P<low>\d{5,6})(?:\s*(?P<curr>USD|EUR|GBP|\$|€|£))"
]

def _clean_number(s: str):
    if s is None: 
        return None
    s = s.replace(",", "").replace(" ", "")
    # handle k shorthand
    if re.search(r"[kK]$", s):
        try:
            val = float(s[:-1])
            # If value is small like "120k", it means 120000. 
            # If it's "120000k" that's weird, but usually context implies 1000s.
            return val * 1000
        except:
            pass
    try:
        return float(s)
    except:
        return None

def extract_salary(text: str):
    if not text:
        return None, None, None
    t = text.replace("\u2013", "-")  # normalize dash
    # quick currency detection
    if re.search(r"\bUSD\b|\bUS\$|\$", t):
        currency = "USD"
    elif re.search(r"\bEUR\b|€", t):
        currency = "EUR"
    elif re.search(r"\bGBP\b|£", t):
        currency = "GBP"
    else:
        # Default to USD if looks like salary but no currency found? 
        # For now, safe default None or maybe 'USD' if user requested? 
        # User prompt didn't strictly say default USD, but logic allows it.
        currency = "USD" 

    for rx in SAL_REGEXPS:
        m = re.search(rx, t, re.IGNORECASE)
        if not m:
            continue
        low = _clean_number(m.groupdict().get("low"))
        high = _clean_number(m.groupdict().get("high"))
        # if low uses 'k' shorthand like 120k handled above
        if low and not high:
            high = low
        
        # Sanity check: if low is < 1000, it's probably hourly or not a salary?
        # If low is < 10000 and NO currency symbol was found in the regex match itself, it's risky (could be a year like 2025)
        # But we handle hourly "50-80 USD".
        
        # Specific fix for the "2025-10" bug (Year 2025 - Month 10?)
        # If the values are like 2000-2030, it's likely a year range.
        # Let's enforce a minimum for "annual looking" salaries.
        
        # If currency provided, we trust it more.
        match_dict = m.groupdict()
        match_curr = match_dict.get("curr") or match_dict.get("prefix")
        
        if not match_curr and (low is None or low < 25000):
            # Without currency, ignore low numbers (likely years, hours, or generic formatting)
            continue

        # Valid Salary Thresholds
        # Hourly min: $15
        # Annual min: $20,000
        # Ignore anything < 15 (even with $) to catch "$4.5 billion" cases where billion wasn't caught
        if low is not None and low < 15: 
            continue
            
        return low, high, currency or match_curr or "USD"
    return None, None, None

# ---------- visa / sponsorship inference ----------
VISA_POSITIVE = [
    "visa sponsorship", "will sponsor", "sponsor h1", "h1b sponsorship", "sponsorship available",
    "will sponsor visa", "h1b", "sponsor", "opt", "cap exempt"
]
VISA_NEGATIVE = [
    "must have authorization", "must be authorized to work", "cannot sponsor", "no visa sponsorship",
    "us citizens", "green card", "work authorization required"
]

def infer_visa(text: str):
    if not text:
        return "unknown", 0.0
    t = text.lower()
    score = 0.0
    for p in VISA_POSITIVE:
        if p in t:
            score += 1.0
    for n in VISA_NEGATIVE:
        if n in t:
            score -= 1.0
    # normalize to 0..1 roughly
    confidence = min(max((score + 1) / 3.0, 0.0), 1.0)
    if score >= 1:
        return "sponsored", confidence
    if score <= -1:
        return "not_sponsored", confidence
    return "possible", confidence


# ========== ENRICHMENT ORCHESTRATOR ==========

def extract_all_enrichment(job_description: str, title: str = ""):
    """
    Orchestrates all enrichment extraction functions.
    This is the main entry point for the Enrichment Layer.
    
    Returns a dictionary with all extracted intelligence:
        {
            "tech_languages": "Python, Rust",
            "tech_frameworks": "Django, React",
            "tech_cloud": "AWS, Docker",
            "tech_data": "PostgreSQL",
            "seniority_tier": "Senior",
            "seniority_level": 4,
            "experience_years": 5,
            "education_level": "Bachelor's",
            "certifications": ["AWS SA"],
            "soft_skills": ["Leadership"],
            "natural_languages": "Spanish",
            "job_summary": "Two sentence summary..."
        }
    """
    if not job_description:
        return {}
    
    # Tech Stack
    tech = extract_tech_stack(job_description)
    
    # Qualifications
    quals = extract_qualifications(job_description, title=title)
    
    # Summary
    summary = generate_noise_free_summary(job_description)
    
    # Merge all into single dictionary
    return {
        "tech_languages": tech.get("languages"),
        "tech_frameworks": tech.get("frameworks"),
        "tech_cloud": tech.get("cloud"),
        "tech_data": tech.get("data"),
        "seniority_tier": quals.get("seniority_tier"),
        "seniority_level": quals.get("seniority_level"),
        "experience_years": quals.get("experience_years"),
        "education_level": quals.get("education_level"),
        "certifications": quals.get("certifications"), 
        "soft_skills": quals.get("soft_skills"),
        "natural_languages": "English", # Todo: extract real lang
        "job_summary": summary
    }
