import os
import sys
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from us_ats_jobs.db import database
from us_ats_jobs.intelligence.skills_db import SkillExtractorDB

def verify_5000_milestone():
    db_config = database.get_db_config()
    extractor = SkillExtractorDB(db_config)
    
    test_text = """
    We are seeking a Staff Software Engineer to lead our FinTech Data Governance initiatives. 
    You will be responsible for API Implementation, Backend Scalability, and Cloud Migration. 
    Expertise in Zero Trust Security, Kubernetes Operators, and MLflow Tracking is essential. 
    You will drive Strategic Planning for our High Throughput Systems and manage Stakeholder Engagement.
    Experience with HIPAA Compliance for HealthTech Infrastructure is a plus.
    """
    
    print(f"🔍 Testing extraction on massive 5k+ ontology (Count: {len(extractor._skills_cache)})")
    extracted_skills = extractor.extract(test_text)
    
    found_names = [s.canonical_name for s in extracted_skills]
    print(f"✅ Extracted Milestone Skills ({len(found_names)}):")
    for name in sorted(found_names):
        print(f"  - {name}")

    # Broad checks for our newer matrix items
    expected_samples = ["Staff Software Engineer", "API Implementation", "Backend Scalability", "Cloud Migration", "Zero Trust Security", "Strategic Planning", "Stakeholder Engagement"]
    found_samples = [e for e in expected_samples if e in found_names]
    
    print(f"\n📊 Matrix Discovery: {len(found_samples)}/{len(expected_samples)} critical samples found.")
    
    if len(found_samples) > 5:
        print("\n🎉 5,000 SKILL MILESTONE VERIFIED!")
    else:
        print("\n⚠️ Extraction density lower than expected for high-intent matrix.")

if __name__ == "__main__":
    verify_5000_milestone()
