import psycopg2
import os
from dotenv import load_dotenv

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, '.env'))

DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("\n" + "="*80)
print("JOB ENRICHMENT STATUS REPORT")
print("="*80 + "\n")

# Get counts
cur.execute("SELECT COUNT(*) FROM job_enrichment")
total_enrichments = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM jobs WHERE enrichment_status = 'completed'")
completed = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM jobs WHERE enrichment_status = 'failed'")
failed = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM jobs WHERE enrichment_status = 'pending'")
pending = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM jobs")
total_jobs = cur.fetchone()[0]

print(f"📊 STATISTICS:")
print(f"   Total Jobs in Database: {total_jobs}")
print(f"   ✅ Successfully Enriched: {completed}")
print(f"   ❌Failed: {failed}")
print(f"   ⏳ Pending: {pending}")
print(f"   📝 Enrichment Records: {total_enrichments}\n")

# Sample enriched jobs
print("="*80)
print("SAMPLE ENRICHED JOBS (First 3)")
print("="*80 + "\n")

cur.execute("""
    SELECT 
        je.job_id, 
        j.title,
        j.company,
        je.tech_languages, 
        je.tech_frameworks,
        je.visa_sponsorship,
        je.salary_data
    FROM job_enrichment je
    JOIN jobs j ON je.job_id = j.job_id
    LIMIT 3
""")

for i, row in enumerate(cur.fetchall(), 1):
    print(f"Job #{i}:")
    print(f"  ID: {row[0]}")
    print(f"  Title: {row[1]}")
    print(f"  Company: {row[2]}")
    print(f"  Languages: {row[3] if row[3] else 'N/A'}")
    print(f"  Frameworks: {row[4] if row[4] else 'N/A'}")
    print(f"  Visa: {row[5] if row[5] else 'N/A'}")
    print(f"  Salary: {row[6] if row[6] else 'N/A'}")
    print()

cur.close()
conn.close()

print("="*80)
print("REPORT COMPLETE")
print("="*80)
