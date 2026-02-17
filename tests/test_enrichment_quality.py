import sys
import os
import json

# Fix import path to include project root AND internal source root
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)
sys.path.append(os.path.join(root_dir, "us_ats_jobs"))

from us_ats_jobs.intelligence.infer import extract_all_enrichment

TEST_CASES = [
    {
        "name": "Senior Backend Engineer",
        "title": "Senior Python Backend Engineer",
        "desc": "We are seeking a Senior Engineer with 5+ years of Python and Django experience. Must have AWS knowledge and strong leadership skills. Experience with PostgreSQL is required.",
    },
    {
        "name": "Junior Frontend Developer",
        "title": "Junior React Developer",
        "desc": "Entry level role for a React enthusiast. 0-2 years experience. Must know JavaScript and CSS. Great communication skills a plus.",
    },
    {
        "name": "DevOps / Cloud Architect",
        "title": "Cloud Solutions Architect",
        "desc": "Requires AWS Certified Solutions Architect certification. Expertise in Kubernetes, Terraform, and Docker. 10 years experience required. Must accept mentorship roles.",
    },
    {
        "name": "Product Manager",
        "title": "Product Manager",
        "desc": "Looking for a PM with Agile and Scrum experience. Strong problem-solving and strategic thinking abilities. MBA preferred.",
    }
]

print("="*80)
print("🔎 ENRICHMENT LOGIC TEST SUITE")
print("="*80)

for case in TEST_CASES:
    print(f"\nTesting Case: {case['name']}")
    print(f"Input Title:  {case['title']}")
    print(f"Input Desc Snippet: {case['desc'][:60]}...")
    
    # Run Extraction
    result = extract_all_enrichment(case['desc'], title=case['title'])
    
    # Display Results
    print(f"\n--- Extracted Metadata ---")
    print(f"  • Seniority:      {result.get('seniority_tier')} (Level {result.get('seniority_level')})")
    print(f"  • Experience:     {result.get('experience_years')} Years")
    print(f"  • Education:      {result.get('education_level')}")
    print(f"  • Tech Languages: {result.get('tech_languages')}")
    print(f"  • Tech Frameworks:{result.get('tech_frameworks')}")
    print(f"  • Cloud/Infra:    {result.get('tech_cloud')}")
    print(f"  • Certifications: {result.get('certifications')}")
    print(f"  • Soft Skills:    {result.get('soft_skills')}")
    print("-" * 80)

print("\n✅ Test Suite Completed.")
