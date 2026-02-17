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
            SELECT COUNT(*) 
            FROM companies c 
            LEFT JOIN career_endpoints ce ON c.id = ce.company_id 
            WHERE ce.id IS NULL AND c.active = TRUE
        """)
        count = cur.fetchone()[0]
        print(f"Orphan Companies (Active but no Endpoint): {count}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    check()
