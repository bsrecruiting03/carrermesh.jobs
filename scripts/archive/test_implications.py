import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from us_ats_jobs.db import database
from us_ats_jobs.intelligence.skills_db import SkillExtractorDB

def test_implications():
    db_config = database.get_db_config()
    extractor = SkillExtractorDB(db_config)
    
    # Qwik is known to imply JavaScript (ID 3)
    test_text = "Highly experienced with Qwik and Vala development."
    
    print(f"🔍 Testing Knowledge Implication for: '{test_text}'")
    skills = extractor.extract(test_text, expand_implications=True)
    
    print(f"\n✅ Extracted Skills ({len(skills)}):")
    for s in sorted(skills, key=lambda x: x.canonical_name):
        source = "Direct" if s.matched_synonym == "ft_match" else "Implication"
        print(f"  - {s.canonical_name:20s} [Source: {source}, Confidence: {s.confidence}]")

    found_names = [s.canonical_name for s in skills]
    if "JavaScript" in found_names and "C" in found_names:
        print("\n🎉 SUCCESS: Implied skills (JavaScript, C) were successfully expanded!")
    else:
        print("\n⚠️ FAILURE: Implied skills were NOT found in results.")

if __name__ == "__main__":
    test_implications()
