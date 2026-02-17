"""
Bulk Company Discovery Script
==============================
This script discovers which ATS (Greenhouse, Lever, Ashby, Workable) 
companies use and automatically adds them to your database.

Usage:
    python bulk_discover.py
"""

import sys
import os

# Add us_ats_jobs to path
sys.path.append(os.path.join(os.path.dirname(__file__), "us_ats_jobs"))

from scripts.discover_companies import discover_and_save

# ============================================================================
# ADD YOUR COMPANIES HERE
# ============================================================================
# Just add company names - the script will automatically find which ATS they use!

COMPANIES_TO_DISCOVER = [
    # ==========================================================================
    # STANDARD ATS COMPANIES (Greenhouse, Lever, Ashby, Workable)
    # ==========================================================================
    # These companies use standard ATS platforms that discovery can find.
    # For Big Tech (Meta, Amazon, Netflix, Microsoft), use CUSTOM ADAPTERS instead.
    
    # AI/ML Startups (Most use Greenhouse/Lever)
    "Hugging Face",
    "Stability AI",
    "Cohere",
    "Midjourney",
    "Anthropic",
    "Scale AI",
    "Weights & Biases",
    "Anyscale",
    "Modal",
    "Replicate",
    
    # Developer Tools & Infrastructure
    "Vercel",
    "Supabase",
    "Railway",
    "Fly.io",
    "Render",
    "Deno",
    "Bun",
    "Prisma",
    "PlanetScale",
    "Neon",
    "Turso",
    "Upstash",
    
    # Fintech Startups
    "Stripe",
    "Plaid",
    "Brex",
    "Ramp",
    "Mercury",
    "Rippling",
    
    # Gaming (Use Greenhouse)
    "Roblox",
    "Unity",
    
    # Ride-sharing (Lyft uses Greenhouse)
    "Lyft",
    
    # E-commerce & Delivery
    "Instacart",
    "DoorDash",
    "Etsy",
    
    # Social & Communication
    "Pinterest",
    "Snap",
    "Discord",
    
    # Cyber Security
    "Crowdstrike",
    "Okta",
    "Auth0",
    "Snyk",
    "Lacework",
    
    # Cloud/Observability
    "Datadog",
    "New Relic",
    "PagerDuty",
    "HashiCorp",
    "Grafana Labs",
    "Chronosphere",
    
    # HR/Fintech
    "Gusto",
    "Deel",
    "Remote",
    "Lattice",
    
    # Add more startups below:
    # "Your Company",
]

# ============================================================================
# DISCOVERY EXECUTION
# ============================================================================

def main():
    print("=" * 80)
    print("🤖 BULK COMPANY DISCOVERY")
    print("=" * 80)
    print(f"\n📋 Total companies to discover: {len(COMPANIES_TO_DISCOVER)}\n")
    
    successful = 0
    failed = 0
    
    for idx, company in enumerate(COMPANIES_TO_DISCOVER, 1):
        print(f"\n[{idx}/{len(COMPANIES_TO_DISCOVER)}] Processing: {company}")
        print("-" * 80)
        
        try:
            discover_and_save(company)
            successful += 1
        except KeyboardInterrupt:
            print("\n\n⚠️  Discovery interrupted by user (Ctrl+C)")
            break
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            failed += 1
        
        # Small delay to avoid rate limiting
        import time
        time.sleep(2)
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 DISCOVERY SUMMARY")
    print("=" * 80)
    print(f"✅ Successful: {successful}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {successful / len(COMPANIES_TO_DISCOVER) * 100:.1f}%")
    print("\n💡 Companies have been added to your database!")
    print("   Run 'python us_ats_jobs/main.py' to fetch jobs from them.\n")

if __name__ == "__main__":
    main()
