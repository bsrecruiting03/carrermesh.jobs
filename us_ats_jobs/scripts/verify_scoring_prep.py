import sys
import os
import sqlite3

# Add parent path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import db.database as database
try:
    from matching.scorer import score_resume_against_job
except ImportError:
    print("❌ Could not import matching.scorer")
    sys.exit(1)

def verify_tables():
    print("🔎 Verifying Phase II Schema...")
    with database.get_connection() as conn:
        tables = ["resumes", "job_matches"]
        for t in tables:
            try:
                # Check if table exists
                cursor = conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{t}'")
                if cursor.fetchone():
                    print(f"  ✅ Table '{t}' exists.")
                else:
                    print(f"  ❌ Table '{t}' MISSING!")
            except Exception as e:
                print(f"  ❌ Error checking '{t}': {e}")

def verify_interface():
    print("\n🔎 Verifying Scorer Interface...")
    resume = "Python Developer with 5 years experience."
    job = {"title": "Senior Python Engineer", "description": "Looking for python experts."}
    
    try:
        result = score_resume_against_job(resume, job)
        print(f"  ✅ Scorer returned: {result}")
        if "overall_score" in result:
             print("  ✅ Contract valid (overall_score present).")
    except Exception as e:
        print(f"  ❌ Scorer failed: {e}")

if __name__ == "__main__":
    verify_tables()
    verify_interface()
