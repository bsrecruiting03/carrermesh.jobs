
import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5433/job_board")

def check_schema():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("Checking column definitions...")
    
    cur.execute("""
        SELECT job_id FROM jobs WHERE job_id LIKE '%JR108971%' LIMIT 1;
    """)
    
    row = cur.fetchone()
    if row:
        print(f"Found Job ID: {repr(row[0])}")
    else:
        print("Job ID not found via Python.")
        
    conn.close()

if __name__ == "__main__":
    check_schema()
