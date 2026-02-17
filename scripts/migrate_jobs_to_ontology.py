"""
Job Location Migration Script

Maps existing 333k+ jobs to the new location_id using the ontology.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor
import re
import logging
from typing import Optional, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:password@127.0.0.1:5433/job_board")


class LocationMatcher:
    """Match job locations to ontology location_ids."""
    
    def __init__(self, conn):
        self.conn = conn
        self.alias_cache = {}
        self.location_cache = {}
        self._load_aliases()
        self._load_locations()
    
    def _load_aliases(self):
        """Load all aliases into memory for fast lookup."""
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT la.alias, la.location_id, l.name, l.type, l.parent_id
            FROM location_aliases la
            JOIN locations l ON la.location_id = l.id
            ORDER BY la.priority DESC
        """)
        for row in cur.fetchall():
            key = row['alias'].lower().strip()
            if key not in self.alias_cache:  # Keep highest priority
                self.alias_cache[key] = {
                    'location_id': row['location_id'],
                    'name': row['name'],
                    'type': row['type'],
                    'parent_id': row['parent_id']
                }
        cur.close()
        logger.info(f"Loaded {len(self.alias_cache)} aliases into cache")
    
    def _load_locations(self):
        """Load all locations into memory."""
        cur = self.conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, name, type, parent_id, iso_code FROM locations")
        for row in cur.fetchall():
            self.location_cache[row['id']] = dict(row)
        cur.close()
        logger.info(f"Loaded {len(self.location_cache)} locations into cache")
    
    def _clean_text(self, text: str) -> str:
        """Clean location text for matching."""
        if not text:
            return ""
        # Remove special chars, normalize whitespace
        text = re.sub(r'[^\w\s,\-]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _extract_parts(self, raw_location: str) -> list:
        """Split location into parts."""
        if not raw_location:
            return []
        
        # Common delimiters
        parts = re.split(r'[,\-/|]', raw_location)
        parts = [p.strip() for p in parts if p.strip()]
        return parts
    
    def match(self, raw_location: str, city: str = None, state: str = None, country: str = None) -> Optional[int]:
        """
        Match a job location to a location_id.
        Returns the most specific location_id found (city > state > country).
        """
        # Try existing normalized fields first
        for field in [state, country]:
            if field:
                key = field.lower().strip()
                if key in self.alias_cache:
                    return self.alias_cache[key]['location_id']
        
        # Parse raw location
        if not raw_location:
            return None
        
        raw_clean = self._clean_text(raw_location)
        parts = self._extract_parts(raw_clean)
        
        best_match = None
        best_type_priority = {'city': 3, 'state': 2, 'country': 1, None: 0}
        
        # Check each part
        for part in parts:
            key = part.lower()
            if key in self.alias_cache:
                match = self.alias_cache[key]
                if best_match is None or best_type_priority.get(match['type'], 0) > best_type_priority.get(best_match['type'], 0):
                    best_match = match
        
        # Also check full string
        full_key = raw_clean.lower()
        if full_key in self.alias_cache:
            match = self.alias_cache[full_key]
            if best_match is None or best_type_priority.get(match['type'], 0) > best_type_priority.get(best_match['type'], 0):
                best_match = match
        
        # Handle Remote - map to parent if found
        if 'remote' in raw_clean.lower():
            # Try to find country context
            for part in parts:
                key = part.lower()
                if key in self.alias_cache and self.alias_cache[key]['type'] == 'country':
                    return self.alias_cache[key]['location_id']
            # Default to USA for unmarked remote
            if 'usa' in self.alias_cache:
                return self.alias_cache['usa']['location_id']
        
        return best_match['location_id'] if best_match else None


def migrate_jobs(batch_size: int = 1000, dry_run: bool = False):
    """Migrate all jobs to use location_id."""
    conn = psycopg2.connect(DATABASE_URL)
    matcher = LocationMatcher(conn)
    
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Count total jobs
    cur.execute("SELECT COUNT(*) FROM jobs WHERE location_id IS NULL")
    total = cur.fetchone()['count']
    logger.info(f"Total jobs to migrate: {total}")
    
    processed = 0
    matched = 0
    unmatched = 0
    last_id = ""
    
    while True:
        cur.execute("""
            SELECT job_id, location, city, state, country
            FROM jobs
            WHERE location_id IS NULL
              AND job_id > %s
            ORDER BY job_id
            LIMIT %s
        """, (last_id, batch_size))
        
        rows = cur.fetchall()
        if not rows:
            break
        
        updates = []
        for row in rows:
            last_id = row['job_id']
            location_id = matcher.match(
                row['location'],
                row.get('city'),
                row.get('state'),
                row.get('country')
            )
            
            if location_id:
                updates.append((location_id, row['job_id']))
                matched += 1
            else:
                unmatched += 1
        
        if updates and not dry_run:
            cur.executemany("""
                UPDATE jobs SET location_id = %s WHERE job_id = %s
            """, updates)
            conn.commit()
        
        processed += len(rows)
        
        if processed % 10000 == 0:
            logger.info(f"Processed {processed}/{total} jobs. Matched: {matched}, Unmatched: {unmatched}")
    
    cur.close()
    conn.close()
    
    logger.info(f"Migration complete! Matched: {matched}, Unmatched: {unmatched}")
    return matched, unmatched


def update_location_counts():
    """Update job_count for each location."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Update direct counts
    cur.execute("""
        UPDATE locations l SET job_count = (
            SELECT COUNT(*) FROM jobs j WHERE j.location_id = l.id
        )
    """)
    
    # Update parent counts (include children)
    cur.execute("""
        UPDATE locations l SET job_count = job_count + COALESCE((
            SELECT SUM(job_count) FROM locations child WHERE child.parent_id = l.id
        ), 0)
        WHERE l.type = 'country'
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    logger.info("Location counts updated!")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Preview without updating')
    args = parser.parse_args()
    
    print("=== Job Location Migration ===")
    matched, unmatched = migrate_jobs(dry_run=args.dry_run)
    
    if not args.dry_run:
        print("\nUpdating location counts...")
        update_location_counts()
    
    print(f"\n✅ Migration complete! Matched: {matched}, Unmatched: {unmatched}")
