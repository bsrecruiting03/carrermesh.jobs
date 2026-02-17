import psycopg2
import os
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

# Load environment
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, '.env'))

DATABASE_URL = os.getenv("DATABASE_URL")

print("=" * 80)
print("DATABASE SCHEMA ANALYSIS")
print("=" * 80)

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor(cursor_factory=RealDictCursor)

# Get schema for each table
tables = ['jobs', 'job_enrichment', 'job_search']

for table_name in tables:
    print(f"\n{'=' * 80}")
    print(f"TABLE: {table_name}")
    print('=' * 80)
    
    # Get columns
    cur.execute(f"""
        SELECT 
            column_name, 
            data_type, 
            character_maximum_length,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position
    """)
    
    columns = cur.fetchall()
    
    if not columns:
        print(f"⚠️  Table '{table_name}' does not exist!")
        continue
    
    print(f"\nColumns ({len(columns)} total):")
    print("-" * 80)
    for col in columns:
        nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
        max_len = f"({col['character_maximum_length']})" if col['character_maximum_length'] else ""
        default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
        print(f"  • {col['column_name']:<30} {col['data_type']}{max_len:<15} {nullable}{default}")

# Get triggers
print(f"\n{'=' * 80}")
print("TRIGGERS")
print('=' * 80)

cur.execute("""
    SELECT 
        trigger_name,
        event_manipulation,
        event_object_table,
        action_statement
    FROM information_schema.triggers
    WHERE event_object_table IN ('jobs', 'job_enrichment', 'job_search')
    ORDER BY event_object_table, trigger_name
""")

triggers = cur.fetchall()
print(f"\nFound {len(triggers)} trigger(s):")
for trigger in triggers:
    print(f"\n  Trigger: {trigger['trigger_name']}")
    print(f"  Table: {trigger['event_object_table']}")
    print(f"  Event: {trigger['event_manipulation']}")
    print(f"  Action: {trigger['action_statement'][:100]}...")

cur.close()
conn.close()

print(f"\n{'=' * 80}")
print("ANALYSIS COMPLETE")
print('=' * 80)
