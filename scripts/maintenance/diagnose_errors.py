import psycopg2
import os
from dotenv import load_dotenv

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, '.env'))

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

try:
    print("\n" + "="*80)
    print("DIAGNOSING RECENT FAILURES (LAST 200)")
    print("="*80 + "\n")
    
    cur.execute("""
        SELECT error_log, COUNT(*) 
        FROM (
            SELECT error_log 
            FROM jobs 
            WHERE enrichment_status = 'failed' 
            ORDER BY updated_at DESC 
            LIMIT 200
        ) sub 
        GROUP BY error_log 
        ORDER BY COUNT(*) DESC
    """)
    
    rows = cur.fetchall()
    if not rows:
        print("No recent failures found.")
    else:
        for error, count in rows:
            print(f"[{count} times] Error: {error}")
            
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
