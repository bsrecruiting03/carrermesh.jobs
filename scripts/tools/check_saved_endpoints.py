import os
import sys
import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

def check():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, ats_provider, ats_slug, canonical_url, active 
            FROM career_endpoints 
            WHERE ats_slug IN ('stripe', 'adidas', 'airbnb')
        """)
        rows = cur.fetchall()
        print(f"Found {len(rows)} Saved Endpoints:")
        for r in rows:
            print(f" - [{r[1]}] {r[2]} -> {r[3]}")
    finally:
        conn.close()

if __name__ == "__main__":
    check()
