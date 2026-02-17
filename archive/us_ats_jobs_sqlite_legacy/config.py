import os

# -------- API KEYS (from environment) --------

JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY")
LINKEDIN_API_KEY = os.getenv("LINKEDIN_API_KEY")
USAJOBS_API_KEY = "TWy97jxU1uP8OVS6+WGViutelodtLV+UrdHsn25eDdA="
USAJOBS_EMAIL = "bsrecruiting03@gmail.com"

# -------- FEATURE FLAGS --------

ENABLE_LINK_USAJOBS = True 
ENABLE_LINKED_WORKDAY = True  # Workday integration (Enabled)
ENABLE_BAMBOOHR = True         # BambooHR integration (2,519 companies)
ENABLE_LINKEDIN = True  
ENABLE_JSEARCH = True
ENABLE_ATS = True  

# -------- PAGINATION --------

JSEARCH_PAGES = 4
LINKEDIN_PAGES = 2
USAJOBS_PAGES = 3  # Increase for more results
USAJOBS_KEYWORDS = ["Software Engineer", "Data Scientist", "Cybersecurity", "DevOps", "IT Specialist"]

# -------- PARALLEL PROCESSING --------

MAX_WORKERS = 10  # Number of concurrent threads for company fetching

# -------- COMPANIES --------

GREENHOUSE_COMPANIES = [
    "airbnb",
    "stripe",
    "coinbase",
    "invision", 
    "miro",
    "notion",
    "lattice",
    "zeplin",
    "hopin",
    "mapbox",
    "chilipiper",
    "scale",
    "figma",
    "mercury",
    "partnerstack",
    "make",
    "descript",
    "zapier",
    "cloudflare",
    "doordash",
    "qualtrics",
    "quora2",
    "stripe",
    "monzo",
    "picnic",
    "blinkist",
    "creativefabrica",
    "lightspeedhq",
    "paypay",
    "applike-group",
    "bandlab",
    "betssongroup",
    "blablacar",
    "bol",
    "catawiki",
    "didi",
    "robinhood",
    "affirm",
    "benchling",
    "coinbase",
    "datadoghq",
    "mongodb",
    "walmart",
    "idexx",
    "column",
    "runreveal",
    "electric-sql",
    "sudowrite",
    "monumental",
    "tangram",
    "atomictessellator",
    "instant",
    "dbos",
    "edgedb",
    "beaconai",
    "billie",
    "adjust",
    
]

LEVER_COMPANIES = [
    "spotify",
    "atlassian",
    "eventbrite",
    "jobgether",
    "vohraphysicians",
    "lifestancehealth",
    "ciandt",
    "paytm",
    "seb",
    "lyrahealth",
    "shieldai",
    "wingassistant",
    "binance",
    "tsmg",
    "ivcevidensia",
    "alignerr",
    "latitudeinc",
    "jiostar",
    "zoox",
    "danielshealth",
    "saronic",
    "applied",
    "palantir",
    "plaid",
    "retool",
    "grammarly",
    "shopify",
    "photoroom",
    "mujininc",
    "intropic",
    "figma",
    "neeva",
    "scaleai",
    "thrive",
    "nightfallai",
    "finn.auto",
]

ASHBY_COMPANIES = [
    "notion",
    "linear",
    "reddit",
    "ramp",
    "scaleai",
    "openai",
    "anthropic",
    "brex",
    "gusto",
    "asana",
    "discord",
    "snowflake",
    "ironclad",
    "snyk",
    "replit",
    "lemonade",
    "clay",
    "deel",
    "zapier",
    "cursor",
    "notion",
    "lyft",
    "github",
    "shopify",
    "ramp",
    "render",
    "junipersquare",
    "cedar",
    "hawk",
    "grow",
    "trainline",
    "newstory",
    "yourremotetechrecruiter",
    "goldenstarlabs",
    "oyster",
    "hopper",
    "replit",
    "lumaai",
    "tacto",
    "thedeveloperlink",
    "cryptio",
    "worldly",
    "unison",
    "theydo",
    "incident",
    "rula",
    "formatone",
    "pragma",
    "brightline",
    "decimal",
    "count",
    "freed",
    "peerbound",

]

WORKABLE_COMPANIES = [
    "canva",
    "shopify",
    "hubspot",
    "atlassian",
    "Man Group",
    "Anza",
    "Trexquant",
    "AI wareen Oil company Inc",
    "Swwep360",
    "Aretum",
    "Domaintools",
    "TP-link systems inc",


]

WORKDAY_COMPANIES = [
    {"name": "Mastercard", "slug": "mastercard"},
    {"name": "NVIDIA", "slug": "nvidia"},
    {"name": "Target", "slug": "target"},
    {"name": "Workday", "slug": "workday"},
    {"name": "Adobe", "slug": "adobe"},
    {"name": "Bank of America", "slug": "bankofamerica"},
    {"name": "Capital One", "slug": "capitalone"},
    {"name": "Raytheon", "slug": "raytheon"},
]


