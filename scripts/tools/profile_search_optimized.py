
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))

from api.config import settings

def profile_search_optimized(term="engineer"):
    conn = None
    try:
        conn = psycopg2.connect(settings.database_url)
        cur = conn.cursor()
        
        print(f"Profiling OPTIMIZED search for term: '{term}'")
        
        # REMOVED similarity from ORDER BY
        query = """
        EXPLAIN ANALYZE
        SELECT 
            j.job_id, 
            ts_rank(j.search_vector, plainto_tsquery('english', %s)) as rank,
            similarity(j.title, %s) as title_sim
        FROM jobs j
        LEFT JOIN job_enrichment e ON j.job_id = e.job_id
        WHERE (j.search_vector @@ plainto_tsquery('english', %s) OR j.title %% %s)
        ORDER BY ts_rank(j.search_vector, plainto_tsquery('english', %s)) DESC, j.date_posted DESC
        LIMIT 20 OFFSET 0;
        """
        
        cur.execute(query, (term, term, term, term, term))
        
        rows = cur.fetchall()
        for row in rows:
            print(row[0])
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    profile_search_optimized()
