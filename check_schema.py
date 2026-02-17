
import psycopg2
import sys

def check_schema():
    try:
        conn = psycopg2.connect(
            dbname="job_board",
            user="postgres",
            password="password",
            host="127.0.0.1",
            port="5433"
        )
        cur = conn.cursor()
        
        tables = ['companies', 'job_search', 'jobs', 'job_enrichment']
        for table in tables:
            print(f"\n--- Table: {table} ---")
            cur.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}'")
            for row in cur.fetchall():
                print(f"{row[0]}: {row[1]}")
                
        conn.close()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    check_schema()
