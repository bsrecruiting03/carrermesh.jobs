
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))

from api.config import settings

def profile_search_hybrid(term="engineer"):
    conn = None
    try:
        conn = psycopg2.connect(settings.database_url)
        cur = conn.cursor()
        
        print(f"Profiling HYBRID (Date-First) search for term: '{term}'")
        
        # Strategy:
        # 1. Inner query finds matches and orders by date (fast index scan)
        # 2. Limit to 1000 candidates
        # 3. Outer query sorts those 1000 by rank/similarity
        query = """
        EXPLAIN ANALYZE
        WITH candidates AS (
            SELECT j.job_id, j.search_vector, j.title, j.date_posted
            FROM jobs j
            WHERE (j.search_vector @@ plainto_tsquery('english', %s) OR j.title %% %s)
            ORDER BY j.date_posted DESC
            LIMIT 1000
        )
        SELECT 
            c.job_id,
            ts_rank(c.search_vector, plainto_tsquery('english', %s)) as rank,
            similarity(c.title, %s) as title_sim
        FROM candidates c
        JOIN jobs j ON c.job_id = j.job_id
        LEFT JOIN job_enrichment e ON c.job_id = e.job_id
        ORDER BY (ts_rank(c.search_vector, plainto_tsquery('english', %s)) + similarity(c.title, %s)) DESC
        LIMIT 20;
        """
        
        cur.execute(query, (term, term, term, term, term, term))
        
        rows = cur.fetchall()
        for row in rows:
            print(row[0])
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    profile_search_hybrid()
