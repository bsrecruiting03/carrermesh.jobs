
import os
import sys
import psycopg2
from dotenv import load_dotenv

# Setup
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)
load_dotenv(os.path.join(root_dir, '.env'))

DATABASE_URL = os.getenv("DATABASE_URL")

print("=== Ollama Worker Test ===\n")

# 1. Insert a test job
print("Step 1: Inserting test job...")
try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Clean up previous test
    cur.execute("DELETE FROM jobs WHERE job_id = 'ollama-test-123'")
    cur.execute("DELETE FROM job_enrichment WHERE job_id = 'ollama-test-123'")
    conn.commit()
    
    # Insert test job
    cur.execute("""
        INSERT INTO jobs (
            job_id, title, company, location, job_description, 
            job_link, source, date_posted, enrichment_status, ingested_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, NOW(), %s, NOW()
        )
    """, (
        'ollama-test-123',
        'Senior Python Developer',
        'Test Company',
        'Remote',
        '''We are seeking a Senior Python Developer with 5+ years of experience. 
        Requirements: Python, Django, FastAPI, PostgreSQL, Docker, Kubernetes, AWS.
        We offer visa sponsorship for qualified candidates.
        Salary: $120,000 - $150,000 per year.
        This is a fully remote position.''',
        'https://test.com/job',
        'test',
        'pending'
    ))
    conn.commit()
    print("✅ Test job inserted")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Database error: {e}")
    sys.exit(1)

# 2. Run worker (will process our test job)
print("\nStep 2: Running worker with Ollama...")
print("(This may take 30-60 seconds for local model inference)\n")

import subprocess
worker_path = os.path.join(root_dir, 'scripts', 'worker_enrichment.py')
process = subprocess.Popen(
    [sys.executable, worker_path],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# Monitor for 90 seconds
import time
start_time = time.time()
while time.time() - start_time < 90:
    line = process.stdout.readline()
    if line:
        print(line.strip())
        if 'ollama-test-123' in line and ('✓ Enriched' in line or 'Enriched' in line):
            print("\n✅ SUCCESS! Job processed by Ollama!")
            process.terminate()
            break
    if process.poll() is not None:
        break
else:
    print("\n⏱️ Timeout - terminating worker")
    process.terminate()

# 3. Check results
print("\nStep 3: Checking enrichment results...")
try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT enrichment_status, error_log 
        FROM jobs 
        WHERE job_id = 'ollama-test-123'
    """)
    job_status = cur.fetchone()
    
    if job_status:
        status, error = job_status
        print(f"Job Status: {status}")
        if error:
            print(f"Error Log: {error}")
    
    cur.execute("""
        SELECT tech_languages, tech_frameworks, visa_sponsorship, salary_data
        FROM job_enrichment 
        WHERE job_id = 'ollama-test-123'
    """)
    enrichment = cur.fetchone()
    
    if enrichment:
        print(f"\n✅ Enrichment Data Found:")
        print(f"  Tech Languages: {enrichment[0]}")
        print(f"  Tech Frameworks: {enrichment[1]}")
        print(f"  Visa Data: {enrichment[2]}")
        print(f"  Salary Data: {enrichment[3]}")
    else:
        print("\n❌ No enrichment data found")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error checking results: {e}")

print("\n=== Test Complete ===")
