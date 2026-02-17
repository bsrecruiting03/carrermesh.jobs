import os
import sys
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from us_ats_jobs.db import database
from us_ats_jobs.intelligence.skills_db import SkillExtractorDB

def verify_extraction():
    db_config = database.get_db_config()
    extractor = SkillExtractorDB(db_config)
    
    test_text = """
    We are looking for a Senior Software Engineer (Tech Lead) to join our team. 
    You will work on Microservices using FastAPI and Go. 
    Experience with Large Language Models (LLM), RAG, and Vector Databases (Pinecone) is a must. 
    You will deploy using Kubernetes and Terraform on AWS.
    Knowledge of CI/CD and MLOps is required.
    """
    
    print("🔍 Testing extraction on sample text...")
    extracted_skills = extractor.extract(test_text)
    
    found_names = [s.canonical_name for s in extracted_skills]
    print(f"✅ Extracted Skills ({len(found_names)}):")
    for name in sorted(found_names):
        print(f"  - {name}")

    # Check for specific expected skills from our new vocabulary
    expected = ["Microservices", "FastAPI", "Go", "Large Language Models", "RAG", "Vector Databases", "Kubernetes", "Terraform", "AWS", "CI/CD", "MLOps"]
    missing = [e for e in expected if e not in found_names]
    
    if not missing:
        print("\n🎉 ALL CRITICAL SKILLS VERIFIED!")
    else:
        print(f"\n⚠️ Missing skills: {missing}")

if __name__ == "__main__":
    verify_extraction()
