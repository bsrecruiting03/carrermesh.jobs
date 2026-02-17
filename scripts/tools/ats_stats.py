import os
import sys
import psycopg2

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

def ats_stats():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT ats_provider, COUNT(*) 
            FROM career_endpoints 
            GROUP BY ats_provider 
            ORDER BY COUNT(*) DESC
        """)
        stats = cur.fetchall()
        
        print(f"\n📊 Distinct ATS Providers Found")
        print(f"-----------------------------")
        total_types = len(stats)
        print(f"✅ Total Types: {total_types}")
        
        for provider, count in stats:
            print(f"   - {provider}: {count:,}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    ats_stats()
