
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Add api to path
sys.path.append(os.path.join(os.getcwd(), 'api'))
from config import settings

def get_db_connection():
    return psycopg2.connect(
        settings.database_url,
        cursor_factory=RealDictCursor
    )

def setup_search():
    conn = get_db_connection()
    conn.autocommit = True
    cur = conn.cursor()

    try:
        print("1. Adding search_vector column...")
        cur.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS search_vector tsvector;")
        
        print("2. Populating search_vector (Base Data)...")
        # Update base fields (Title, Company, Description)
        # Using coalesce to handle nulls
        update_base_sql = """
            UPDATE jobs
            SET search_vector = 
                setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(company, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(job_description, '')), 'C');
        """
        cur.execute(update_base_sql)
        
        print("3. Populating search_vector (Enrichment Skills)...")
        # Concatenate enrichment skills into the vector with weight A
        update_skills_sql = """
            UPDATE jobs j
            SET search_vector = j.search_vector ||
                setweight(
                    to_tsvector(
                        'english', 
                        coalesce(e.tech_languages, '') || ' ' || 
                        coalesce(e.tech_frameworks, '') || ' ' || 
                        coalesce(e.tech_cloud, '') || ' ' ||
                        coalesce(e.tech_tools, '')
                    ), 
                    'A'
                )
            FROM job_enrichment e
            WHERE j.job_id = e.job_id;
        """
        cur.execute(update_skills_sql)

        print("4. Creating GIN Index...")
        cur.execute("CREATE INDEX IF NOT EXISTS jobs_search_vector_idx ON jobs USING GIN (search_vector);")
        
        print("5. Verifying Search Ranking...")
        test_query = "python developer"
        verify_sql = """
            SELECT title, company, ts_rank(search_vector, plainto_tsquery('english', %s)) as rank
            FROM jobs
            WHERE search_vector @@ plainto_tsquery('english', %s)
            ORDER BY rank DESC
            LIMIT 5;
        """
        cur.execute(verify_sql, (test_query, test_query))
        results = cur.fetchall()
        
        print(f"\nTop 5 matches for '{test_query}':")
        for r in results:
            print(f"[{r['rank']:.4f}] {r['title']} at {r['company']}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    setup_search()
