"""Quick script to inspect database schema for API planning."""
import os
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/job_board")

def inspect_schema():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=" * 80)
    print("COMPANIES TABLE SCHEMA")
    print("=" * 80)
    cur.execute("""
        SELECT column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'companies'
        ORDER BY ordinal_position;
    """)
    for row in cur.fetchall():
        nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
        length = f"({row['character_maximum_length']})" if row['character_maximum_length'] else ""
        print(f"  {row['column_name']:<20} {row['data_type']}{length:<15} {nullable}")
    
    print("\n" + "=" * 80)
    print("JOBS TABLE SCHEMA")
    print("=" * 80)
    cur.execute("""
        SELECT column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'jobs'
        ORDER BY ordinal_position;
    """)
    for row in cur.fetchall():
        nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
        length = f"({row['character_maximum_length']})" if row['character_maximum_length'] else ""
        print(f"  {row['column_name']:<20} {row['data_type']}{length:<15} {nullable}")
    
    print("\n" + "=" * 80)
    print("DATABASE STATISTICS")
    print("=" * 80)
    
    cur.execute("SELECT COUNT(*) as total FROM companies WHERE active = true;")
    print(f"  Active Companies: {cur.fetchone()['total']}")
    
    cur.execute("SELECT COUNT(*) as total FROM jobs;")
    print(f"  Total Jobs: {cur.fetchone()['total']}")
    
    cur.execute("""
        SELECT ats_provider, COUNT(*) as count 
        FROM companies 
        WHERE active = true 
        GROUP BY ats_provider 
        ORDER BY count DESC;
    """)
    print("\n  Companies by ATS Provider:")
    for row in cur.fetchall():
        print(f"    {row['ats_provider']:<15} {row['count']:>6}")
    
    cur.execute("""
        SELECT 
            COUNT(DISTINCT location) as unique_locations,
            COUNT(DISTINCT department) as unique_departments
        FROM jobs;
    """)
    stats = cur.fetchone()
    print(f"\n  Unique Locations: {stats['unique_locations']}")
    print(f"  Unique Departments: {stats['unique_departments']}")
    
    # Sample job to see data structure
    print("\n" + "=" * 80)
    print("SAMPLE JOB RECORD")
    print("=" * 80)
    cur.execute("SELECT * FROM jobs LIMIT 1;")
    sample = cur.fetchone()
    if sample:
        for key, value in sample.items():
            display_value = str(value)[:100] if value else "NULL"
            print(f"  {key:<20} {display_value}")
    
    cur.close()
    conn.close()
    print("\n" + "=" * 80)

if __name__ == "__main__":
    inspect_schema()
