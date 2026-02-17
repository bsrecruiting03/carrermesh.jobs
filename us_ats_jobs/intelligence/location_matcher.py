"""
Location Matcher Utility
Standardizes raw location strings against the project's location ontology.
"""

import re
import logging
from typing import Optional, Dict, List
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

class LocationMatcher:
    """
    Matches job locations to ontology location_ids.
    Caches aliases and locations for extreme performance (sub-millisecond).
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LocationMatcher, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self, db_config: Optional[any] = None):
        if self.initialized:
            return
            
        self.db_config = db_config
        self.alias_cache = {}
        self.location_cache = {}
        self.initialized = True
        
        if db_config:
            self.refresh_cache()

    def refresh_cache(self):
        """Load all aliases and locations into memory."""
        try:
            if isinstance(self.db_config, dict):
                conn = psycopg2.connect(**self.db_config)
            else:
                conn = psycopg2.connect(self.db_config)
                
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Load aliases
                cur.execute("""
                    SELECT la.alias, la.location_id, l.name, l.type, l.parent_id
                    FROM location_aliases la
                    JOIN locations l ON la.location_id = l.id
                    ORDER BY la.priority DESC
                """)
                self.alias_cache = {}
                for row in cur.fetchall():
                    key = row['alias'].lower().strip()
                    if key not in self.alias_cache:
                        self.alias_cache[key] = {
                            'location_id': row['location_id'],
                            'name': row['name'],
                            'type': row['type'],
                            'parent_id': row['parent_id']
                        }
                
                # Load locations
                cur.execute("SELECT id, name, type, parent_id, iso_code FROM locations")
                self.location_cache = {row['id']: dict(row) for row in cur.fetchall()}
                
            conn.close()
            logger.info(f"🧠 LocationMatcher: Loaded {len(self.alias_cache)} aliases and {len(self.location_cache)} locations.")
        except Exception as e:
            logger.error(f"❌ LocationMatcher: Failed to load cache: {e}")

    def _clean_text(self, text: str) -> str:
        if not text: return ""
        text = re.sub(r'[^\w\s,\-]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _extract_parts(self, raw_location: str) -> List[str]:
        if not raw_location: return []
        parts = re.split(r'[,\-/|]', raw_location)
        return [p.strip() for p in parts if p.strip()]

    def match(self, raw_location: str) -> Optional[int]:
        """
        Match a raw location string to a location_id.
        Priority: Direct Match > City > State > Country
        """
        if not raw_location or not self.alias_cache:
            return None
            
        clean_text = self._clean_text(raw_location)
        parts = self._extract_parts(clean_text)
        
        best_match = None
        type_priority = {'city': 3, 'state': 2, 'country': 1, None: 0}
        
        # 1. Full string match
        full_key = clean_text.lower()
        if full_key in self.alias_cache:
            best_match = self.alias_cache[full_key]
            
        # 2. Part matches (look for most specific)
        for part in parts:
            key = part.lower()
            if key in self.alias_cache:
                match = self.alias_cache[key]
                if not best_match or type_priority.get(match['type'], 0) > type_priority.get(best_match['type'], 0):
                    best_match = match
                    
        # 3. Remote Handling
        if 'remote' in clean_text.lower() and not best_match:
            # Try to find a country context if possible, otherwise default USA for safety in this project context
            if 'usa' in self.alias_cache:
                return self.alias_cache['usa']['location_id']
                
        return best_match['location_id'] if best_match else None

# Global helper for singleton access
_matcher = None

def get_matcher(db_config=None):
    global _matcher
    if _matcher is None:
        _matcher = LocationMatcher(db_config)
    return _matcher
