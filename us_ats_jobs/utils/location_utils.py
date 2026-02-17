import re

# Mapping for US States
US_STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire',
    'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina',
    'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania',
    'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota', 'TN': 'Tennessee',
    'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington',
    'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
}

# Mapping for common country variants
COUNTRY_VARIANTS = {
    'US': 'USA', 'U.S.': 'USA', 'UNITED STATES': 'USA', 'U.S.A.': 'USA',
    'UK': 'United Kingdom', 'U.K.': 'United Kingdom',
    'UAE': 'United Arab Emirates',
}

# Common city mappings
CITY_MAPPINGS = {
    'NYC': ('New York', 'New York', 'USA'),
    'LONDON': ('London', None, 'United Kingdom'),
    'SF': ('San Francisco', 'California', 'USA'),
}

REVERSE_STATES = {v.upper(): k for k, v in US_STATES.items()}

def normalize_location(location_text):
    """
    Standardizes a location string into City, State, Country.
    """
    if not location_text or not isinstance(location_text, str):
        return {"city": None, "state": None, "country": None, "full": "Unknown"}

    # Clean up common prefixes
    text = re.sub(r'^(Remote|On-site|Hybrid)[\s\-\,]*', '', location_text, flags=re.IGNORECASE)
    text = text.strip()

    # Quick check for known city abbreviations
    if text.upper() in CITY_MAPPINGS:
        c, s, co = CITY_MAPPINGS[text.upper()]
        return {"city": c, "state": s, "country": co, "full": f"{c}, {s or ''}, {co}".replace(", ,", ",")}

    # Split by comma or semicolon
    parts = [p.strip() for p in re.split(r'[,;]', text)]
    
    city = None
    state = None
    country = None

    if len(parts) >= 3:
        city = parts[0]
        state = US_STATES.get(parts[1].upper(), parts[1])
        country = COUNTRY_VARIANTS.get(parts[2].upper(), parts[2])
    elif len(parts) == 2:
        p1_up = parts[0].upper()
        p2_up = parts[1].upper()
        
        if p2_up in US_STATES:
            city = parts[0]
            state = US_STATES[p2_up]
            country = "USA"
        elif p2_up in COUNTRY_VARIANTS or p2_up == "USA" or p2_up == "UNITED STATES":
            # Part 2 is country. What is part 1?
            if p1_up in US_STATES:
                state = US_STATES[p1_up]
                country = COUNTRY_VARIANTS.get(p2_up, "USA" if "US" in p2_up else p2_up)
            else:
                city = parts[0]
                country = COUNTRY_VARIANTS.get(p2_up, "USA" if "US" in p2_up else p2_up)
        else:
            city = parts[0]
            country = parts[1]
    elif len(parts) == 1:
        p = parts[0].upper()
        if p in COUNTRY_VARIANTS:
            country = COUNTRY_VARIANTS[p]
        elif p == "USA":
            country = "USA"
        elif p in US_STATES:
            state = US_STATES[p]
            country = "USA"
        else:
            city = parts[0]

    # Final cleanup
    if country:
        country_up = country.upper()
        if country_up in COUNTRY_VARIANTS:
            country = COUNTRY_VARIANTS[country_up]
        elif "UNITED STATES" in country_up:
            country = "USA"

    if state and not country:
        country = "USA"

    full_parts = [p for p in [city, state, country] if p]
    full_str = ", ".join(full_parts) if full_parts else text

    return {
        "city": city,
        "state": state,
        "country": country,
        "full": full_str
    }
