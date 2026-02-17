
import psycopg2
import sys
import os

# Add root path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api.config import settings

def clean_db():
    print("Connecting...")
    try:
        # Direct connection (bypass pool)
        conn = psycopg2.connect(settings.database_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Finding blocked queries...")
        cur.execute("""
            SELECT pid, state, query, wait_event_type, query_start
            FROM pg_stat_activity 
            WHERE state = 'idle in transaction' 
            AND pid != pg_backend_pid()
        """)
        
        rows = cur.fetchall()
        print(f"Found {len(rows)} idle transactions.")
        
        for row in rows:
            pid = row[0]
            print(f"Killing PID {pid} (Query: {row[2][:50]}...)")
            cur.execute(f"SELECT pg_terminate_backend({pid})")
            
        print("Complete.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clean_db()
