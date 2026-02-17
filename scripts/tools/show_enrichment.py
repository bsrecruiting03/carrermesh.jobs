
import psycopg2
import os
import json
from dotenv import load_dotenv

load_dotenv('../.env')

def show_latest_jobs():
    try:
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cur = conn.cursor()
        
        query = """
            SELECT 
                j.title, 
                j.company, 
                je.tech_languages, 
                je.tech_frameworks, 
                je.visa_sponsorship, 
                je.salary_data, 
                je.remote_policy,
                je.soft_skills
            FROM jobs j 
            JOIN job_enrichment je ON j.job_id = je.job_id 
            ORDER BY je.last_enriched_at DESC 
            LIMIT 3
        """
        
        cur.execute(query)
        rows = cur.fetchall()
        
        print(f"\n--- LATEST ENRICHED JOBS PREVIEW ({len(rows)} found) ---\n")
        
        for r in rows:
            print(f"🔹 Job: {r[0]} at {r[1]}")
            print(f"   Stack: {r[2]} + {r[3]}")
            print(f"   Soft Skills: {r[7]}")
            
            # Format Visa
            visa = r[4]
            if visa:
                visa_status = "✅ SPONSORED" if visa.get('mentioned') else "❌ No info"
                print(f"   Visa: {visa_status} (Conf: {visa.get('confidence',0)}%)")
            else:
                print("   Visa: Not extracted")
                
            # Format Salary
            sal = r[5]
            if sal and sal.get('extracted'):
                print(f"   Salary: ${sal.get('min', '?'):,} - ${sal.get('max', '?'):,}")
            else:
                print("   Salary: Not specified")
                
            print(f"   Remote: {r[6]}\n")
            
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    show_latest_jobs()
