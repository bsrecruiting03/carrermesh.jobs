import psycopg2
import os

PG_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/job_board")

def check_indexes():
    print(f"🔍 Checking Indexes on {PG_URL}...")
    try:
        conn = psycopg2.connect(PG_URL)
        cur = conn.cursor()
        
        # Query to list all indexes
        cur.execute("""
            SELECT tablename, indexname, indexdef 
            FROM pg_indexes 
            WHERE schemaname = 'public' 
            ORDER BY tablename, indexname;
        """)
        
        indexes = cur.fetchall()
        
        if not indexes:
            print("⚠️  No indexes found in public schema!")
            return

        print(f"\n{'Table':<20} | {'Index Name':<30}")
        print("-" * 55)
        for table, name, _ in indexes:
             print(f"{table:<20} | {name:<30}")
             
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_indexes()
