"""
Enterprise Giants Registry - Direct Career Endpoints

CORRECTED ATS CATEGORIZATION (User Verified):
1. Workday: CVS, eBay, Salesforce, PayPal, Adobe, Target, CapitalOne, Nvidia, Snap, Walmart, Uber, etc.
2. Custom Portals: Tesla, Apple, Microsoft, Amazon, TikTok, Google, Meta
3. Oracle Taleo: JPMC, Ford, Oracle, Goldman Sachs
4. BrassRing (IBM): IBM
5. Greenhouse: Discord, Figma, Stripe, etc. (already supported)
"""

import os
import sys
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import psycopg2

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("EnterpriseRegistry")

DATABASE_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

# =============================================================================
# VERIFIED WORKDAY ENDPOINTS
# =============================================================================

WORKDAY_GIANTS = {
    # Format: "company_name": ("tenant.shard.myworkdayjobs.com", "site_path")
    
    # Retail & Consumer
    "walmart": ("walmart.wd5.myworkdayjobs.com", "WalmartExternal"),
    "target": ("target.wd5.myworkdayjobs.com", "targetcareers"),
    "cvshealth": ("cvshealth.wd1.myworkdayjobs.com", "CVS_Health_Careers"),
    "costco": ("costco.wd5.myworkdayjobs.com", "CostcoCareers"),
    
    # Tech Giants (Workday-based)
    "nvidia": ("nvidia.wd5.myworkdayjobs.com", "NVIDIAExternalCareerSite"),
    "salesforce": ("salesforce.wd12.myworkdayjobs.com", "External_Career_Site"),
    "adobe": ("adobe.wd5.myworkdayjobs.com", "external_experienced"),
    "snap": ("snap.wd5.myworkdayjobs.com", "Snap"),
    "ebay": ("ebay.wd5.myworkdayjobs.com", "apply"),
    "uber": ("uber.wd5.myworkdayjobs.com", "Uber"),
    "netflix": ("netflix.wd5.myworkdayjobs.com", "external"),
    "hubspot": ("hubspot.wd1.myworkdayjobs.com", "HubSpotCareers"),
    "redhat": ("redhat.wd5.myworkdayjobs.com", "Jobs"),
    
    # Finance (Workday-based)
    "capitalone": ("capitalone.wd12.myworkdayjobs.com", "Capital_One"),
    "paypal": ("paypal.wd5.myworkdayjobs.com", "Jobs"),
    "fidelity": ("fmr.wd1.myworkdayjobs.com", "FidelityCareers"),
    "bankofamerica": ("ghr.wd12.myworkdayjobs.com", "boaborocareers"),
    
    # Auto & Manufacturing (Workday-based)
    "toyota": ("toyota.wd5.myworkdayjobs.com", "TMNA_Careers"),
    "gm": ("gm.wd5.myworkdayjobs.com", "Careers_Ext"),
    
    # Aerospace & Defense
    "boeing": ("boeing.wd1.myworkdayjobs.com", "EXTERNAL_CAREERS"),
    "lockheedmartin": ("lockheedmartin.wd5.myworkdayjobs.com", "external"),
    
    # Healthcare & Pharma
    "pfizer": ("pfizer.wd1.myworkdayjobs.com", "Pfizer_Careers"),
    
    # Other Giants
    "alight": ("alight.wd1.myworkdayjobs.com", "Alight"),
    "priceline": ("priceline.wd5.myworkdayjobs.com", "careers"),
    "marriott": ("marriott.wd5.myworkdayjobs.com", "marriottjobs"),
}

# =============================================================================
# CUSTOM CAREER PORTALS (Need special scrapers)
# =============================================================================

CUSTOM_PORTALS = {
    "google": {
        "url": "https://careers.google.com/jobs/results/",
        "api": "https://careers.google.com/api/v3/search/",
        "type": "custom_google"
    },
    "apple": {
        "url": "https://jobs.apple.com/en-us/search",
        "api": "https://jobs.apple.com/api/role/search",
        "type": "custom_apple"
    },
    "meta": {
        "url": "https://www.metacareers.com/jobs",
        "api": "https://www.metacareers.com/graphql",
        "type": "custom_meta"
    },
    "microsoft": {
        "url": "https://careers.microsoft.com/",
        "api": "https://gcsservices.careers.microsoft.com/search/api/v1/search",
        "type": "custom_microsoft"
    },
    "amazon": {
        "url": "https://www.amazon.jobs/",
        "api": "https://www.amazon.jobs/en/search.json",
        "type": "custom_amazon"
    },
    "tesla": {
        "url": "https://www.tesla.com/careers/search",
        "api": "https://www.tesla.com/cua-api/careers/search",
        "type": "custom_tesla"
    },
    "tiktok": {
        "url": "https://careers.tiktok.com/",
        "api": "https://careers.tiktok.com/api/v1/search",
        "type": "custom_tiktok"
    },
    "bytedance": {
        "url": "https://jobs.bytedance.com/",
        "api": "https://jobs.bytedance.com/api/v1/search",
        "type": "custom_bytedance"
    },
}

# =============================================================================
# ORACLE TALEO (Need Taleo adapter)
# =============================================================================

TALEO_GIANTS = {
    "oracle": {
        "url": "https://oracle.taleo.net/careersection/2/jobsearch.ftl",
        "company": "Oracle"
    },
    "jpmorgan": {
        "url": "https://jpmc.taleo.net/careersection/2/jobsearch.ftl",
        "company": "JPMorgan Chase"
    },
    "goldmansachs": {
        "url": "https://goldmansachs.taleo.net/careersection/2/jobsearch.ftl",
        "company": "Goldman Sachs"
    },
    "ford": {
        "url": "https://ford.taleo.net/careersection/2/jobsearch.ftl",
        "company": "Ford Motor Company"
    },
}

# =============================================================================
# BRASSRING (IBM's ATS)
# =============================================================================

BRASSRING_GIANTS = {
    "ibm": {
        "url": "https://careers.ibm.com/",
        "api": "https://careers.ibm.com/api/jobs",
        "company": "IBM"
    },
}

# =============================================================================
# GREENHOUSE (Already supported - just slugs)
# =============================================================================

GREENHOUSE_GIANTS = [
    "discord", "figma", "stripe", "notion", "databricks",
    "snowflake", "datadog", "cloudflare", "plaid", "instacart",
    "coinbase", "airtable", "linear", "vercel", "supabase"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}


def verify_workday_endpoint(tenant_domain: str, site_path: str) -> tuple:
    """Verify if a Workday endpoint is active."""
    tenant = tenant_domain.split('.')[0]
    api_url = f"https://{tenant_domain}/wday/cxs/{tenant}/{site_path}/jobs"
    
    payload = {"limit": 1, "offset": 0, "appliedFacets": {}, "searchText": ""}
    
    try:
        response = requests.post(api_url, json=payload, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            return True, total, None
        return False, 0, f"HTTP {response.status_code}"
    except Exception as e:
        return False, 0, str(e)


def register_workday_endpoints():
    """Verify and register all Workday giants."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    logger.info(f"🏢 Registering {len(WORKDAY_GIANTS)} Workday Endpoints...")
    
    registered = 0
    verified = 0
    
    for company, (tenant_domain, site_path) in WORKDAY_GIANTS.items():
        canonical_url = f"https://{tenant_domain}/{site_path}"
        
        success, job_count, error = verify_workday_endpoint(tenant_domain, site_path)
        
        if success:
            verified += 1
            logger.info(f"  ✅ {company}: {job_count} jobs")
            
            try:
                cur.execute("""
                    INSERT INTO career_endpoints (
                        canonical_url, ats_provider, ats_slug,
                        discovered_from, confidence_score, last_verified_at, active
                    ) VALUES (%s, 'workday', %s, 'enterprise_registry', 1.0, NOW(), TRUE)
                    ON CONFLICT (canonical_url) DO UPDATE SET
                        confidence_score = 1.0,
                        last_verified_at = NOW(),
                        active = TRUE
                """, (canonical_url, f"{company}/{site_path}"))
                conn.commit()
                registered += 1
            except Exception as e:
                conn.rollback()
                logger.error(f"  ❌ {company}: {e}")
        else:
            logger.warning(f"  ⚠️ {company}: {error}")
    
    conn.close()
    
    logger.info("=" * 50)
    logger.info(f"📊 Workday: {verified}/{len(WORKDAY_GIANTS)} verified, {registered} registered")
    return verified, registered


def register_custom_portals():
    """Register custom portal companies."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    logger.info(f"🌐 Registering {len(CUSTOM_PORTALS)} Custom Portals...")
    
    for company, info in CUSTOM_PORTALS.items():
        try:
            cur.execute("""
                INSERT INTO career_endpoints (
                    canonical_url, ats_provider, ats_slug,
                    discovered_from, confidence_score, active
                ) VALUES (%s, %s, %s, 'enterprise_registry', 1.0, TRUE)
                ON CONFLICT (canonical_url) DO NOTHING
            """, (info['url'], info['type'], company))
            conn.commit()
            logger.info(f"  📝 {company}: {info['type']}")
        except Exception as e:
            conn.rollback()
            logger.error(f"  ❌ {company}: {e}")
    
    conn.close()


def register_taleo_endpoints():
    """Register Oracle Taleo-based companies."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    logger.info(f"🏛️ Registering {len(TALEO_GIANTS)} Taleo Endpoints...")
    
    for company, info in TALEO_GIANTS.items():
        try:
            cur.execute("""
                INSERT INTO career_endpoints (
                    canonical_url, ats_provider, ats_slug,
                    discovered_from, confidence_score, active
                ) VALUES (%s, 'taleo', %s, 'enterprise_registry', 1.0, TRUE)
                ON CONFLICT (canonical_url) DO NOTHING
            """, (info['url'], company))
            conn.commit()
            logger.info(f"  📝 {company}: taleo ({info['company']})")
        except Exception as e:
            conn.rollback()
            logger.error(f"  ❌ {company}: {e}")
    
    conn.close()


def register_brassring_endpoints():
    """Register BrassRing-based companies (IBM)."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    logger.info(f"🔧 Registering {len(BRASSRING_GIANTS)} BrassRing Endpoints...")
    
    for company, info in BRASSRING_GIANTS.items():
        try:
            cur.execute("""
                INSERT INTO career_endpoints (
                    canonical_url, ats_provider, ats_slug,
                    discovered_from, confidence_score, active
                ) VALUES (%s, 'brassring', %s, 'enterprise_registry', 1.0, TRUE)
                ON CONFLICT (canonical_url) DO NOTHING
            """, (info['url'], company))
            conn.commit()
            logger.info(f"  📝 {company}: brassring")
        except Exception as e:
            conn.rollback()
            logger.error(f"  ❌ {company}: {e}")
    
    conn.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Enterprise Giants Registry')
    parser.add_argument('--workday', action='store_true', help='Register Workday')
    parser.add_argument('--custom', action='store_true', help='Register Custom portals')
    parser.add_argument('--taleo', action='store_true', help='Register Taleo')
    parser.add_argument('--brassring', action='store_true', help='Register BrassRing')
    parser.add_argument('--all', action='store_true', help='Register all')
    args = parser.parse_args()
    
    if args.all:
        register_workday_endpoints()
        register_custom_portals()
        register_taleo_endpoints()
        register_brassring_endpoints()
    else:
        if args.workday:
            register_workday_endpoints()
        if args.custom:
            register_custom_portals()
        if args.taleo:
            register_taleo_endpoints()
        if args.brassring:
            register_brassring_endpoints()
        
        if not any([args.workday, args.custom, args.taleo, args.brassring]):
            register_workday_endpoints()


if __name__ == "__main__":
    main()
