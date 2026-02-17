import os
import logging
import meilisearch
from typing import Optional, List, Dict, Any, Tuple
from ..config import settings

logger = logging.getLogger("MeiliRemote")

class MeiliSearchService:
    def __init__(self):
        self.url = os.getenv("MEILI_URL", "http://127.0.0.1:7700")
        self.key = os.getenv("MEILI_MASTER_KEY", "masterKey")
        try:
            self.client = meilisearch.Client(self.url, self.key)
            self.index = self.client.index('jobs')
        except Exception as e:
            logger.error(f"Failed to connect to Meilisearch: {e}")
            self.client = None
            self.index = None

    def search_jobs(
        self,
        query: Optional[str] = None,
        location: Optional[str] = None,
        remote: Optional[bool] = None,
        department: Optional[str] = None,
        tech_stack: Optional[str] = None,
        min_salary: Optional[int] = None,
        max_salary: Optional[int] = None,
        visa_sponsorship: Optional[str] = None,
        remote_policy: Optional[str] = None,
        seniority: Optional[str] = None,
        posted_since: Optional[str] = None,
        sort: str = "date_posted",
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[Dict], int]:
        
        if not self.index:
            # Fallback or error if Meilisearch is down
            # ideally we fallback to DB, but for now lets return empty or error
            logger.error("Meilisearch client not initialized")
            return [], 0

        # Build Filters
        filter_expressions = []

        if location:
            # Use location ontology to resolve aliases and apply proper filter
            # Import here to avoid circular imports
            from ..database import resolve_location
            
            resolved = resolve_location(location)
            if resolved:
                canonical_name = resolved['name']
                loc_type = resolved['type']
                
                if loc_type == 'country':
                    # Filter by country name (exact match)
                    filter_expressions.append(f"country = '{canonical_name}'")
                elif loc_type == 'state':
                    # Filter by state name (exact match)
                    filter_expressions.append(f"state = '{canonical_name}'")
                elif loc_type == 'city':
                    # Filter by city name (exact match)
                    filter_expressions.append(f"city = '{canonical_name}'")
                    
                logger.info(f"[MEILI_LOCATION] Resolved '{location}' -> {loc_type}='{canonical_name}'")
            else:
                # Unknown location - don't filter, let text search handle it
                # This will be appended to query string later
                logger.info(f"[MEILI_LOCATION] Could not resolve '{location}', will use text search")
             
        if remote is not None:
            if remote:
                filter_expressions.append("(is_remote = true OR work_mode = 'remote' OR work_mode = 'hybrid')")
            # else: dont filter, show all? or show only onsite? 'remote=false' usually means "I don't care" or "Onsite only"?
            # Usually: boolean toggle "Remote Only".
        
        if department:
            filter_expressions.append(f"department = '{department}'") # Exact match required for facets

        if tech_stack:
            # tech_stack="Python,React"
            # We want documents that have Python AND React? Or OR?
            # Usually OR for search, AND for strict requirement.
            # Let's do OR for now.
            techs = [t.strip() for t in tech_stack.split(',')]
            tech_filters = []
            for t in techs:
                # tech_languages is an array in Meili. "tech_languages = 'Python'" works for array contains.
                tech_filters.append(f"tech_languages = '{t}'")
                tech_filters.append(f"tech_frameworks = '{t}'")
                tech_filters.append(f"tech_tools = '{t}'")
                tech_filters.append(f"specializations = '{t}'")
            
            if tech_filters:
                filter_expressions.append(f"({' OR '.join(tech_filters)})")

        if min_salary:
            filter_expressions.append(f"salary_max >= {min_salary}") 
        
        if max_salary:
            filter_expressions.append(f"salary_min <= {max_salary}")

        if visa_sponsorship:
             filter_expressions.append(f"visa_sponsorship = '{visa_sponsorship}'")

        if posted_since:
             import datetime
             days = int(posted_since.rstrip('d'))
             cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
             filter_expressions.append(f"date_posted >= '{cutoff}'")

        # Sort
        sort_opts = []
        if sort == 'date_posted':
            sort_opts.append('date_posted:desc')
        elif sort == 'salary':
            sort_opts.append('salary_max:desc')
        
        # Pagination
        offset = (page - 1) * limit

        # Search Params
        search_params = {
            'offset': offset,
            'limit': limit,
            'filter': ' AND '.join(filter_expressions) if filter_expressions else None,
            'sort': sort_opts,
            'facets': ['department', 'work_mode', 'tech_languages', 'specializations', 'city'], 
            'hitsPerPage': limit,
            'page': page
        }

        # Query
        # If no query string, use placeholder
        q_str = query if query else ""
        
        # Only append location to search text if it was NOT resolved by ontology
        # (If resolved, we're already filtering by country/state/city)
        if location:
            from ..database import resolve_location
            if not resolve_location(location):
                # Unknown location - append to search text
                if not query:
                    q_str = location
                else:
                    q_str += f" {location}"

        try:
            result = self.index.search(q_str, search_params)
            return result['hits'], result.get('estimatedTotalHits', result.get('totalHits', 0))
        except Exception as e:
            logger.error(f"❌ Meilisearch search failed: {e}")
            # Degraded mode: try common search without complex parameters if it was a parameter error
            try:
                logger.info("Attempting degraded search (no facets/filters)...")
                basic_result = self.index.search(q_str, {'limit': limit, 'offset': offset})
                return basic_result['hits'], basic_result.get('estimatedTotalHits', 0)
            except Exception as e2:
                logger.error(f"❌ Degraded search also failed: {e2}")
                return [], 0

# Global Instance
search_service = MeiliSearchService()
