import os
import sys
import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

def check_failures():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM career_endpoints WHERE consecutive_failures > 0")
        count = cur.fetchone()[0]
        
        print(f"❌ Failed Endpoints: {count}")
        
        if count > 0:
            cur.execute("""
                SELECT last_failure_reason, COUNT(*) 
                FROM career_endpoints 
                WHERE consecutive_failures > 0 
                GROUP BY last_failure_reason 
                ORDER BY COUNT(*) DESC 
                LIMIT 5
            """)
            reasons = cur.fetchall()
            print("Top Reasons:")
            for reason, c in reasons:
                print(f"  - {reason}: {c}")
                
    finally:
        conn.close()

if __name__ == "__main__":
    check_failures()
