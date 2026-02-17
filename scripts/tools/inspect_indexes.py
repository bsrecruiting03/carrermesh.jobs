
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../api")))

from api.config import settings

def check_indexes():
    try:
        conn = psycopg2.connect(settings.database_url)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print("Checking Indexes on 'jobs' table...")
        cur.execute("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'jobs';
        """)
        
        indexes = cur.fetchall()
        for idx in indexes:
            print(f"- {idx['indexname']}: {idx['indexdef']}")
            
        print("\nChecking Extension 'pg_trgm'...")
        cur.execute("SELECT * FROM pg_extension WHERE extname = 'pg_trgm';")
        ext = cur.fetchone()
        print(f"pg_trgm installed: {ext is not None}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    check_indexes()
