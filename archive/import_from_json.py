"""
Import Companies from JSON
===========================
Reads companies from a JSON file and adds them to the database.

JSON Format:
{
  "greenhouse": ["company1", "company2"],
  "lever": ["company3", "company4"],
  "ashby": ["company5"],
  "workable": ["company6"],
  "bamboohr": ["company7"]
}
"""

import json
import sys
import os

# Add us_ats_jobs to path
sys.path.append(os.path.join(os.path.dirname(__file__), "us_ats_jobs"))

import db.database as database
database.create_tables()

# ATS URL Templates
ATS_TEMPLATES = {
    "greenhouse": {
        "ats_url": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs",
        "career_url": "https://boards.greenhouse.io/{slug}"
    },
    "lever": {
        "ats_url": "https://api.lever.co/v3/postings/{slug}",
        "career_url": "https://jobs.lever.co/{slug}"
    },
    "ashby": {
        "ats_url": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
        "career_url": "https://jobs.ashbyhq.com/{slug}"
    },
    "workable": {
        "ats_url": "https://apply.workable.com/api/v1/widget/accounts/{slug}",
        "career_url": "https://apply.workable.com/{slug}"
    },
    "bamboohr": {
        "ats_url": "https://{slug}.bamboohr.com/jobs",
        "career_url": "https://{slug}.bamboohr.com/jobs"
    },
    "workday": {
        "ats_url": "https://{slug}", 
        "career_url": "https://{slug}"
    }
}

def import_from_json(json_file_path):
    """
    Import companies from a JSON file.
    """
    print("=" * 80)
    print("📥 IMPORTING COMPANIES FROM JSON")
    print("=" * 80)
    print(f"\nReading from: {json_file_path}\n")
    
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {json_file_path}")
        print("\n💡 Create a JSON file with this format:")
        print("""
{
  "greenhouse": ["company1", "company2"],
  "lever": ["company3", "company4"],
  "ashby": ["company5"],
  "workable": ["company6"],
  "bamboohr": ["company7"]
}
        """)
        return
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON format: {e}")
        return
    
    # Statistics
    stats = {
        "total": 0,
        "added": 0,
        "skipped": 0,
        "by_ats": {}
    }
    
    # Process each ATS provider
    for provider, companies in data.items():
        provider_lower = provider.lower()
        
        if provider_lower not in ATS_TEMPLATES:
            print(f"⚠️  Unknown ATS provider: {provider} - skipping")
            continue
        
        print(f"\n📦 Processing {provider.upper()} ({len(companies)} companies)")
        print("-" * 80)
        
        template = ATS_TEMPLATES[provider_lower]
        added_count = 0
        skipped_count = 0
        
        for slug in companies:
            slug = slug.strip()
            if not slug:
                continue
            
            stats["total"] += 1
            
            # Format URLs
            ats_url = template["ats_url"].format(slug=slug)
            career_url = template["career_url"].format(slug=slug)
            
            # Add to database
            try:
                result = database.add_company(
                    name=slug,
                    ats_url=ats_url,
                    ats_provider=provider_lower,
                    career_page_url=career_url,
                    domain=None  # Will be discovered later if needed
                )
                
                if result:
                    print(f"  ✅ Added: {slug}")
                    added_count += 1
                    stats["added"] += 1
                else:
                    print(f"  ⏭️  Skipped (already exists): {slug}")
                    skipped_count += 1
                    stats["skipped"] += 1
                    
            except Exception as e:
                print(f"  ❌ Error adding {slug}: {e}")
                stats["skipped"] += 1
        
        stats["by_ats"][provider] = {
            "added": added_count,
            "skipped": skipped_count,
            "total": len(companies)
        }
    
    # Print Summary
    print("\n" + "=" * 80)
    print("📊 IMPORT SUMMARY")
    print("=" * 80)
    print(f"\n✅ Total Added: {stats['added']}")
    print(f"⏭️  Total Skipped: {stats['skipped']}")
    print(f"📈 Total Processed: {stats['total']}")
    
    print("\n📊 Breakdown by ATS:")
    for provider, counts in stats["by_ats"].items():
        print(f"\n  {provider.upper()}:")
        print(f"    - Total: {counts['total']}")
        print(f"    - Added: {counts['added']}")
        print(f"    - Skipped: {counts['skipped']}")
    
    print("\n" + "=" * 80)
    print("🎉 Import Complete!")
    print("=" * 80)
    print("\n💡 Next Steps:")
    print("   1. Run 'python us_ats_jobs/main.py' to fetch jobs")
    print("   2. Run 'python diag_db.py' to verify imports")
    print()

def main():
    # Default JSON file
    default_json = "companies.json"
    
    # Check if user provided a file path
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = default_json
    
    # Import
    import_from_json(json_file)

if __name__ == "__main__":
    main()
