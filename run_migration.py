"""
Run database migration using psycopg2
"""
import psycopg2

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5433,
    "database": "job_board",
    "user": "postgres",
    "password": "password"
}

# Read migration SQL
with open('migrations/001_create_skills_ontology_tables.sql', 'r', encoding='utf-8') as f:
    migration_sql = f.read()

# Connect and execute
print("Connecting to database...")
conn = psycopg2.connect(**DB_CONFIG)
conn.autocommit = True
cur = conn.cursor()

print("Running migration...")
try:
    cur.execute(migration_sql)
    print("✓ Migration completed successfully!")
    
    # Verify tables created
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name IN ('skills', 'job_skills', 'concepts', 'skill_concepts')
        ORDER BY table_name
    """)
    
    tables = cur.fetchall()
    print(f"\n✓ Created {len(tables)} tables:")
    for table in tables:
        print(f"  - {table[0]}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    raise
finally:
    cur.close()
    conn.close()

print("\n✓ Step 1 Complete: Database migration successful!")
