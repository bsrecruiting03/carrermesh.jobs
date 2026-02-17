"""
Test the resume matcher with real data from the database using Hybrid Search
"""
import psycopg2
import os
import sys

# Add root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from us_ats_jobs.resume.matcher import MatchEngine
from api import database as db
from us_ats_jobs.intelligence.extractor_layer2 import Layer2VectorExtractor

# Database connection logic
os.environ["DATABASE_URL"] = "postgresql://postgres:password@postgres:5432/job_board"
# Initialize DB pool
db.init_db_pool()

# Sample resume
test_resume_text = """
John Doe
Senior Python Developer
San Francisco, CA

Summary:
Senior Software Engineer with 6 years of experience in Python, Django, Flask, and AWS.
Expert in building scalable backend systems and RESTful APIs.
Experienced with PostgreSQL, Docker, and Kubernetes.
Strong leadership skills and team management experience.

Skills:
Python, Django, Flask, FastAPI, JavaScript, React, AWS, Docker, Kubernetes, PostgreSQL, Redis, Celery.
"""

print("=" * 80)
print("TESTING HYBRID SEARCH (DATABASE LAYER)")
print("=" * 80)

# 1. Generate Resume Embedding
print("\n1. Generating Resume Embedding...")
extractor = Layer2VectorExtractor()
resume_vector = extractor.embed_text(test_resume_text)
print(f"   Generated vector of size: {len(resume_vector)}")

# 2. Extract Skills (for hard filter)
print("\n2. Extracting Skills...")
engine = MatchEngine()
processed = engine.process_resume(test_resume_text)
skills = list(processed['skills'])
print(f"   Extracted {len(skills)} skills: {', '.join(skills[:5])}...")

# 3. Test Hybrid Search
print("\n3. Running db.search_jobs_hybrid()...")
try:
    # Use the vector we generated
    candidates = db.search_jobs_hybrid(
        embedding=resume_vector,
        limit=20,
        tech_skills=skills,
        country="United States"
    )
    
    print(f"\n✅ Hybrid Search returned {len(candidates)} candidates!")
    
    if candidates:
        print(f"\nTop Matches from DB:")
        for i, job in enumerate(candidates[:5], 1):
            print(f"{i}. {job['title']} at {job['company']}")
            print(f"   Semantic Score: {job.get('semantic_score', 0):.4f}")
            print(f"   Location: {job.get('location')}")
            print(f"   Tech: {job.get('tech_languages')}")
            print()
            
            # Verify scoring
            score = engine.score_job(processed, job)
            print(f"   -> Final Score: {score['total_score']:.2f}")
            print("-" * 40)
            
    else:
        print("⚠️ No candidates found. Check if job_enrichment table has embeddings.")
        # Debug count
        with db.get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM job_enrichment WHERE embedding IS NOT NULL")
                count = cur.fetchone()['count']
                print(f"   Debug: Found {count} jobs with embeddings in DB.")

except Exception as e:
    print(f"❌ Error during search: {e}")
    import traceback
    traceback.print_exc()

