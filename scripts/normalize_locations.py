"""
Location Normalization Script (Global)

This script normalizes job location data in the PostgreSQL database:
1. Parses raw location strings into City, State/Region, Country components.
2. Standardizes Country names using pycountry (ISO 3166).
3. Normalizes US State codes (e.g., "California" -> "CA").
"""

import os
import sys
import re
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor
import pycountry
import us

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database connection - use the correct URL from .env
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:password@127.0.0.1:5433/job_board")


class LocationNormalizer:
    """Normalizes location strings to City, State, Country components (Global)."""
    
    def __init__(self):
        # Build country lookup from pycountry
        self.country_lookup = {}
        for country in pycountry.countries:
            # Map various forms to the standard name
            self.country_lookup[country.name.lower()] = country.name
            self.country_lookup[country.alpha_2.lower()] = country.name
            self.country_lookup[country.alpha_3.lower()] = country.name
            
            # Handle common name if exists (e.g., "United States" for "United States of America")
            if hasattr(country, 'common_name'):
                self.country_lookup[country.common_name.lower()] = country.name
        
        # Add common variations not in pycountry
        self.country_lookup["usa"] = "United States"
        self.country_lookup["u.s.a."] = "United States"
        self.country_lookup["u.s."] = "United States"
        self.country_lookup["america"] = "United States"
        self.country_lookup["uk"] = "United Kingdom"
        self.country_lookup["england"] = "United Kingdom"
        self.country_lookup["uae"] = "United Arab Emirates"
        self.country_lookup["korea"] = "Korea, Republic of"
        self.country_lookup["south korea"] = "Korea, Republic of"
        
        logger.info(f"Loaded {len(self.country_lookup)} country mappings")
        
        # Build US state lookup from 'us' library
        self.us_state_lookup = {}
        for state in us.states.STATES:
            self.us_state_lookup[state.name.lower()] = state.abbr
            self.us_state_lookup[state.abbr.lower()] = state.abbr
        
        # Add US territories
        for territory in us.states.TERRITORIES:
            self.us_state_lookup[territory.name.lower()] = territory.abbr
            self.us_state_lookup[territory.abbr.lower()] = territory.abbr
            
        logger.info(f"Loaded {len(self.us_state_lookup)} US state/territory mappings")
    
    def normalize(self, raw_location: str) -> dict:
        """
        Parse raw location string into normalized components.
        Returns: {"city": str, "state": str, "country": str}
        """
        if not raw_location:
            return {"city": None, "state": None, "country": None}
        
        # Clean the string
        location = raw_location.strip()
        
        # Remove common prefixes like "Remote - ", "Hybrid - "
        location = re.sub(r'^(Remote|Hybrid|On-?site)\s*[-–]\s*', '', location, flags=re.IGNORECASE)
        
        # Split by common delimiters
        parts = re.split(r'[,;/\-–]', location)
        parts = [p.strip() for p in parts if p.strip()]
        
        city = None
        state = None
        country = None
        
        remaining_parts = []
        
        # Process parts in reverse (country usually last)
        for part in reversed(parts):
            part_lower = part.lower().strip()
            
            # Check if it's a country
            if part_lower in self.country_lookup and country is None:
                country = self.country_lookup[part_lower]
                continue
            
            # Check if it's a US state (only if country is US or not yet determined)
            if part_lower in self.us_state_lookup and state is None:
                state = self.us_state_lookup[part_lower]
                # If we found a US state, country is likely USA
                if country is None:
                    country = "United States"
                continue
            
            remaining_parts.insert(0, part)
        
        # Remaining parts are likely city
        if remaining_parts:
            city = remaining_parts[0]  # Take first as city
        
        # Handle special case: "Remote" as location
        if raw_location.lower().strip() == "remote":
            city = "Remote"
        
        return {
            "city": city,
            "state": state,
            "country": country
        }


def normalize_all_locations(batch_size: int = 1000, dry_run: bool = False):
    """
    Normalize all job locations in the database.
    """
    normalizer = LocationNormalizer()
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Count total jobs
    cur.execute("SELECT COUNT(*) as count FROM jobs")
    total = cur.fetchone()['count']
    logger.info(f"Total jobs to process: {total}")
    
    # Process in batches
    offset = 0
    updated = 0
    skipped = 0
    
    while offset < total:
        cur.execute("""
            SELECT job_id, location, city, state, country 
            FROM jobs 
            ORDER BY job_id
            LIMIT %s OFFSET %s
        """, (batch_size, offset))
        
        jobs = cur.fetchall()
        
        for job in jobs:
            job_id = job['job_id']
            raw_location = job['location']
            
            # Skip if already fully normalized
            if job['city'] and job['country']:
                skipped += 1
                continue
            
            # Normalize
            normalized = normalizer.normalize(raw_location)
            
            # Update
            if not dry_run:
                cur.execute("""
                    UPDATE jobs 
                    SET city = COALESCE(%s, city),
                        state = COALESCE(%s, state),
                        country = COALESCE(%s, country)
                    WHERE job_id = %s
                """, (
                    normalized['city'],
                    normalized['state'],
                    normalized['country'],
                    job_id
                ))
            
            updated += 1
        
        if not dry_run:
            conn.commit()
        
        offset += batch_size
        logger.info(f"Processed {min(offset, total)}/{total} jobs. Updated: {updated}, Skipped: {skipped}")
    
    cur.close()
    conn.close()
    
    logger.info(f"Normalization complete! Updated: {updated}, Skipped: {skipped}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Normalize job location data (Global)")
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for processing")
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    
    normalize_all_locations(batch_size=args.batch_size, dry_run=args.dry_run)
