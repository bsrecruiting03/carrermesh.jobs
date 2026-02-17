"""
Quick verification script to check MIND ontology integration in enrichment pipeline
"""
import psycopg2

conn = psycopg2.connect('postgresql://postgres:postgres@localhost:5433/job_board')
cur = conn.cursor()

# Check job_enrichment with skill_ids
print("="*60)
print("MIND ONTOLOGY INTEGRATION VERIFICATION")
print("="*60)

cur.execute("""
    SELECT COUNT(*) 
    FROM job_enrichment 
    WHERE skill_ids IS NOT NULL AND array_length(skill_ids, 1) > 0
""")
enriched_count = cur.fetchone()[0]
print(f"\n1. Jobs in job_enrichment with skill_ids: {enriched_count:,}")

# Check job_skills with enrichment source
cur.execute("""
    SELECT COUNT(DISTINCT job_id) 
    FROM job_skills 
    WHERE extraction_source = 'enrichment'
""")
job_skills_count = cur.fetchone()[0]
print(f"2. Jobs in job_skills from enrichment: {job_skills_count:,}")

# Sample enriched job
cur.execute("""
    SELECT e.job_id, j.title, e.extracted_skill_count, array_length(e.skill_ids, 1)
    FROM job_enrichment e
    JOIN jobs j ON e.job_id = j.job_id
    WHERE e.skill_ids IS NOT NULL 
    ORDER BY e.last_enriched_at DESC
    LIMIT 3
""")
print(f"\n3. Sample enriched jobs:")
print("-"*60)
for job_id, title, skill_count, array_len in cur.fetchall():
    print(f"   {title[:50]:50} | {skill_count} skills")

# Check total skill extractions
cur.execute("""
    SELECT COUNT(*) 
    FROM job_skills 
    WHERE extraction_source = 'enrichment'
""")
total_skills = cur.fetchone()[0]
print(f"\n4. Total skill extractions from enrichment: {total_skills:,}")

print("\n" + "="*60)
print("✓ Verification complete!")
print("="*60)

cur.close()
conn.close()
