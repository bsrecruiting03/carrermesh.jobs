import psycopg2
import os
from dotenv import load_dotenv

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, '.env'))

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

try:
    print("\n--- JOBS TABLE COLUMNS ---")
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'jobs'")
    for row in cur.fetchall():
        print(row[0])
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
