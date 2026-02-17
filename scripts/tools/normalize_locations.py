
import sys
import os
import psycopg2
from psycopg2.extras import execute_values
import usaddress
import pycountry
import re
from tqdm import tqdm
import concurrent.futures

# Add root path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api.config import settings

# Configuration
BATCH_SIZE = 5000
WORKERS = 4
DB_URL = settings.database_url

# State Mappings
US_STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
    'DC': 'District of Columbia'
}

INDIA_STATES = {
    'AP': 'Andhra Pradesh', 'AR': 'Arunachal Pradesh', 'AS': 'Assam', 'BR': 'Bihar', 'CG': 'Chhattisgarh',
    'GA': 'Goa', 'GJ': 'Gujarat', 'HR': 'Haryana', 'HP': 'Himachal Pradesh', 'JH': 'Jharkhand',
    'KA': 'Karnataka', 'KL': 'Kerala', 'MP': 'Madhya Pradesh', 'MH': 'Maharashtra', 'MN': 'Manipur',
    'ML': 'Meghalaya', 'MZ': 'Mizoram', 'NL': 'Nagaland', 'OD': 'Odisha', 'PB': 'Punjab',
    'RJ': 'Rajasthan', 'SK': 'Sikkim', 'TN': 'Tamil Nadu', 'TS': 'Telangana', 'TR': 'Tripura',
    'UP': 'Uttar Pradesh', 'UK': 'Uttarakhand', 'WB': 'West Bengal',
    'AN': 'Andaman and Nicobar Islands', 'CH': 'Chandigarh', 'DN': 'Dadra and Nagar Haveli and Daman and Diu',
    'DL': 'Delhi', 'JK': 'Jammu and Kashmir', 'LA': 'Ladakh', 'LD': 'Lakshadweep', 'PY': 'Puducherry'
}

# Reverse mapping for normalization check (Full Name -> Standard Full Name)
# This handles casing differences
NORMALIZED_STATES = {v.upper(): v for v in US_STATES.values()}
NORMALIZED_STATES.update({v.upper(): v for v in INDIA_STATES.values()})

def get_db_connection():
    return psycopg2.connect(DB_URL)

def normalize_text(text):
    if not text: return None
    clean = text.strip()
    # Apply casing fixes if known state
    if clean.upper() in NORMALIZED_STATES:
        return NORMALIZED_STATES[clean.upper()]
    return clean

def normalize_state(raw_state, country_code=None):
    """Normalize state abbreviation to full name."""
    if not raw_state: return None
    
    clean = raw_state.strip().upper()
    
    # Check US
    if country_code in ['US', 'USA', 'United States'] or not country_code:
        if clean in US_STATES:
            return US_STATES[clean]
            
    # Check India
    if country_code in ['IN', 'IND', 'India']:
        if clean in INDIA_STATES:
            return INDIA_STATES[clean]
            
    # Generic full match check
    if clean in NORMALIZED_STATES:
         return NORMALIZED_STATES[clean]
         
    return raw_state.strip() # Return original if no mapping found

def parse_location(raw_loc):
    """
    Parses a raw location string into (City, State, Country).
    Prioritizes USA logic via usaddress, then heuristic fallback.
    """
    if not raw_loc:
        return None, None, None
    
    clean_loc = raw_loc.strip()
    if not clean_loc:
        return None, None, None

    # Default containers
    city, state, country = None, None, None

    # Check for explicit country first
    upper_loc = clean_loc.upper()
    
    # 1. Try to detect country from end of string
    detected_country_code = None
    
    # Simple suffix check for our target countries
    for code, full_name in COUNTRY_MAP.items():
        # Check if string ends with " USA" or ", USA" etc
        # Patterns: ", USA", " USA", " United States"
        if upper_loc.endswith(" " + code) or upper_loc.endswith("," + code) or upper_loc.endswith(", " + code):
            country = full_name
            detected_country_code = code
            break
        
        # Check full name
        if full_name.upper() in upper_loc: # Be careful with this loose check, but for end of string it's usually safe
             country = full_name
             detected_country_code = code
             break

    # 2. USA Logic (usaddress is very good for US/Canada addresses)
    # If we either detected US/CA or detected nothing (default assumption often US in this dataset)
    if country in ['United States', 'Canada'] or country is None:
        try:
            tagged, address_type = usaddress.tag(clean_loc)
            if 'PlaceName' in tagged:
                city = tagged['PlaceName']
            if 'StateName' in tagged:
                # Normalize state abbreviation if found
                state = normalize_state(tagged['StateName'], 'US')
            if 'CountryName' in tagged and not country:
                 # Map parsed country if we didn't already have one
                 raw_c = tagged['CountryName'].upper()
                 country = COUNTRY_MAP.get(raw_c, raw_c.title())
            
            # Helper: If state is present but structure is "City, State", easy win
            if not city and ',' in clean_loc:
                parts = [p.strip() for p in clean_loc.split(',')]
                if len(parts) == 2 and len(parts[1]) == 2: # "Austin, TX"
                     city = parts[0]
                     state = normalize_state(parts[1], 'US')
                     if not country: country = 'United States'

        except usaddress.RepeatedLabelError:
            # Fallback for complex strings usaddress can't handle
            pass
        except Exception:
            pass

    # 3. Fallback Heuristics for International / Failed US parse
    if not city:
        parts = [p.strip() for p in clean_loc.split(',')]
        count = len(parts)
        
        if count == 1:
            # Just "New York" or "USA"
            if parts[0].upper() in COUNTRY_MAP:
                country = COUNTRY_MAP[parts[0].upper()]
            else:
                 pass

        elif count == 2:
            # "City, State" or "City, Country"
            # If 2nd part is in COUNTRY_MAP, it's City, Country
            if parts[1].upper() in COUNTRY_MAP:
                city = parts[0]
                country = COUNTRY_MAP[parts[1].upper()]
            # If 2nd part is 2 chars, assume US State -> City, State, US
            elif len(parts[1]) == 2 and parts[1].isalpha():
                city = parts[0]
                state = normalize_state(parts[1], 'US')
                if not country: country = 'United States'
            else:
                # Assume City, Region
                city = parts[0]
                # Try to normalize region as a state (US or India)
                # If country is known as India, use IN logic
                target_code = 'IN' if country == 'India' else ('US' if country == 'United States' else None)
                state = normalize_state(parts[1], target_code)

        elif count >= 3:
            # "City, State, Country"
            if parts[-1].upper() in COUNTRY_MAP:
                country = COUNTRY_MAP[parts[-1].upper()]
                
                target_code = 'IN' if country == 'India' else ('US' if country == 'United States' else None)
                state = normalize_state(parts[-2], target_code)
                
                city = parts[0] # Take first part as city
            else:
                # assume "City, State, Zip" -> US
                city = parts[0]
                state = normalize_state(parts[1], 'US')
    
    # Final cleanup
    if not country and state and len(state) == 2:
         # Strong heuristic: 2 letter state usually implies US/CA. Default US for this dataset context
         country = 'United States'
         # Re-normalize just in case
         state = normalize_state(state, 'US')

    return normalize_text(city), normalize_text(state), normalize_text(country)

def process_batch(batch):
    conn = get_db_connection()
    cur = conn.cursor()
    
    updates = []
    
    try:
        for job_id, raw_loc in batch:
            city, state, country = parse_location(raw_loc)
            if city or state or country:
                updates.append((city, state, country, job_id))
        
        if not updates:
            return 0

        update_query = """
            UPDATE jobs AS j
            SET city = v.city,
                state = v.state,
                country = v.country,
                normalized_location = 
                    COALESCE(v.city, '') || 
                    (CASE WHEN v.city IS NOT NULL AND v.state IS NOT NULL THEN ', ' ELSE '' END) || 
                    COALESCE(v.state, '') || 
                    (CASE WHEN (v.city IS NOT NULL OR v.state IS NOT NULL) AND v.country IS NOT NULL THEN ', ' ELSE '' END) || 
                    COALESCE(v.country, '')
            FROM (VALUES %s) AS v(city, state, country, job_id)
            WHERE j.job_id = v.job_id
        """
        
        execute_values(cur, update_query, updates)
        conn.commit()
        return len(updates)
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
        return 0
    finally:
        cur.close()
        conn.close()

def main():
    print("Starting Location Normalization...")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Only fetch jobs with a raw location
    cur.execute("SELECT job_id, location FROM jobs WHERE location IS NOT NULL AND (city IS NULL OR country IS NULL)")
    all_jobs = cur.fetchall()
    total_jobs = len(all_jobs)
    cur.close()
    conn.close()
    
    print(f"Found {total_jobs} jobs to normalize.")
    
    if total_jobs == 0:
        return

    # Chunk Data
    batches = [all_jobs[i:i + BATCH_SIZE] for i in range(0, len(all_jobs), BATCH_SIZE)]
    
    print(f"Processing in parallel with {WORKERS} workers...")
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=WORKERS) as executor:
        futures = [executor.submit(process_batch, batch) for batch in batches]
        
        processed = 0
        with tqdm(total=total_jobs, unit="jobs") as pbar:
            for future in concurrent.futures.as_completed(futures):
                count = future.result()
                processed += count
                pbar.update(count) # This updates by batch size roughly, strictly we should return actual count processed
                
    print(f"\nDone! Normalized {processed} locations.")

if __name__ == "__main__":
    main()
