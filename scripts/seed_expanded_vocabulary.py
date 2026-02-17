import json
import os
import sys
import psycopg2
from psycopg2.extras import execute_values

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from us_ats_jobs.db import database

def seed_vocabulary():
    vocab_path = os.path.join(os.path.dirname(__file__), "..", "us_ats_jobs", "intelligence", "job_description_vocabulary.json")
    
    if not os.path.exists(vocab_path):
        print(f"❌ Vocabulary file not found: {vocab_path}")
        return

    with open(vocab_path, "r") as f:
        data = json.load(f)

    with database.get_connection() as conn:
        try:
            with conn.cursor() as cur:
                for category in data["job_terminology"]:
                    category_name = category["category"]
                    print(f"📦 Seeding Category: {category_name}")
                    
                    for item in category["items"]:
                        name = item["name"]
                        synonyms = item.get("synonyms", [])
                        
                        # Determine type based on category
                        skill_type = "technical"
                        if "Role" in category_name:
                            skill_type = "role"
                        elif category_name in ["Architecture", "AI/ML & Generative AI"]:
                            skill_type = "capability"

                        # Upsert skill
                        cur.execute("""
                            INSERT INTO skills (canonical_name, synonyms, technical_domains, skill_type)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (canonical_name) DO UPDATE SET
                                synonyms = EXCLUDED.synonyms,
                                technical_domains = EXCLUDED.technical_domains,
                                skill_type = EXCLUDED.skill_type,
                                updated_at = NOW()
                        """, (name, synonyms, [category_name], [skill_type]))
                
                print("✅ Successfully seeded expanded vocabulary!")
                
        except Exception as e:
            print(f"❌ Error seeding vocabulary: {e}")

if __name__ == "__main__":
    seed_vocabulary()
