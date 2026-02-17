
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))

from api.config import settings

def profile_search_strict(term="engineer"):
    conn = None
    try:
        conn = psycopg2.connect(settings.database_url)
        cur = conn.cursor()
        
        print(f"Profiling STRICT (No Fuzzy) search for term: '{term}'")
        
        # Strategy: Strict FTS only. No 'title % term'.
        # This allows Postgres to use the GIN index on search_vector effectively for ranking if possible, 
        # or at least reduces the row count.
        query = """
        EXPLAIN ANALYZE
        SELECT 
            j.job_id, 
            ts_rank(j.search_vector, plainto_tsquery('english', %s)) as rank
        FROM jobs j
        WHERE j.search_vector @@ plainto_tsquery('english', %s)
        ORDER BY ts_rank(j.search_vector, plainto_tsquery('english', %s)) DESC, j.date_posted DESC
        LIMIT 20 OFFSET 0;
        """
        
        cur.execute(query, (term, term, term))
        
        rows = cur.fetchall()
        for row in rows:
            print(row[0])
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    profile_search_strict()
