
import psycopg2
import sys

def count_jobs():
    try:
        conn = psycopg2.connect(
            dbname="job_board",
            user="postgres",
            password="password",
            host="127.0.0.1",
            port="5433"
        )
        cur = conn.cursor()
        
        tables = ['jobs', 'job_enrichment']
        for table in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"Count of rows in '{table}': {count}")
            except Exception as e:
                print(f"Error counting table '{table}': {e}")
                
        # Also check distinct companies if useful
        try:
            cur.execute("SELECT COUNT(DISTINCT company_name) FROM jobs")
            company_count = cur.fetchone()[0]
            print(f"Count of distinct companies in 'jobs': {company_count}")
        except Exception as e:
             print(f"Error counting distinct companies: {e}")

        conn.close()
    except Exception as e:
        print(f"Database connection error: {e}")

if __name__ == "__main__":
    count_jobs()
