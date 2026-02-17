"""
Quick script to analyze implies_skills distribution in MIND database
"""
import psycopg2
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@postgres:5432/job_board")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# 1. Top skills by implies_skills count
print("=== TOP 20 SKILLS BY IMPLIED RELATIONSHIPS ===")
cur.execute("""
    SELECT canonical_name, array_length(implies_skills, 1) as count
    FROM skills
    WHERE array_length(implies_skills, 1) > 0
    ORDER BY count DESC
    LIMIT 20
""")
for name, count in cur.fetchall():
    print(f"{name:30s}: {count} implied skills")

# 2. Distribution analysis
print("\n=== IMPLIES_SKILLS DISTRIBUTION ===")
cur.execute("""
    SELECT 
        CASE 
            WHEN array_length(implies_skills, 1) IS NULL THEN '0'
            WHEN array_length(implies_skills, 1) <= 2 THEN '1-2'
            WHEN array_length(implies_skills, 1) <= 5 THEN '3-5'
            WHEN array_length(implies_skills, 1) <= 10 THEN '6-10'
            ELSE '11+'
        END as bucket,
        COUNT(*) as skill_count
    FROM skills
    GROUP BY bucket
    ORDER BY bucket
""")
for bucket, count in cur.fetchall():
    print(f"{bucket:10s}: {count:4d} skills")

# 3. Average implies count
cur.execute("""
    SELECT AVG(array_length(implies_skills, 1))
    FROM skills
    WHERE array_length(implies_skills, 1) > 0
""")
avg = cur.fetchone()[0]
print(f"\nAverage implies_skills count: {avg:.2f}")

conn.close()
