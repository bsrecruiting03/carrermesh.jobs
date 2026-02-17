import psycopg2
import sys

try:
    print("Connecting to postgresql://postgres:postgres@127.0.0.1:5433/job_board...")
    conn = psycopg2.connect("postgresql://postgres:postgres@127.0.0.1:5433/job_board", connect_timeout=5)
    print("SUCCESS: Connected!")
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f"FAILURE: {e}")
    sys.exit(1)
