
import psycopg2

DB_URL = "postgresql://postgres:postgres@localhost:5433/job_board"

def inspect_jobs_table():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'jobs';
    """)
    
    columns = cur.fetchall()
    print("Columns in 'jobs' table:")
    for col in columns:
        print(f"  - {col[0]} ({col[1]})")
        
    conn.close()

if __name__ == "__main__":
    inspect_jobs_table()
