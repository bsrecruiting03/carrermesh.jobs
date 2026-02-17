"""
Workday Discovery CLI

Main entry point for running Workday tenant discovery.

Usage:
    python run_workday_discovery.py --companies "NVIDIA" "Dell" "Cisco"
    python run_workday_discovery.py --fortune500 --batch-size 30
    python run_workday_discovery.py --import-existing
    python run_workday_discovery.py --validate-existing --limit 50
    python run_workday_discovery.py --stats
"""

import sys
import os
import argparse
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workday_discovery import WorkdayTenantDiscoveryEngine, DiscoveryConfig


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%H:%M:%S'
    )


def main():
    parser = argparse.ArgumentParser(
        description="Workday Tenant Discovery Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Discover tenants for specific companies
  python run_workday_discovery.py --companies "NVIDIA" "Dell" "Cisco"
  
  # Discover from Fortune 500 companies
  python run_workday_discovery.py --fortune500 --batch-size 30
  
  # Import existing tenants from companies.json
  python run_workday_discovery.py --import-existing
  
  # Validate existing tenants in registry
  python run_workday_discovery.py --validate-existing --limit 50
  
  # Show statistics
  python run_workday_discovery.py --stats
        """
    )
    
    # Discovery sources
    parser.add_argument(
        "--companies", 
        nargs="+", 
        help="Specific company names to discover"
    )
    parser.add_argument(
        "--fortune500", 
        action="store_true", 
        help="Run discovery on Fortune 500 companies"
    )
    
    # Import/validate existing
    parser.add_argument(
        "--import-existing", 
        action="store_true",
        help="Import existing Workday tenants from companies.json to registry"
    )
    parser.add_argument(
        "--validate-existing", 
        action="store_true",
        help="Validate existing tenants in the registry"
    )
    
    # Configuration
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=30,
        help="Number of companies per batch (default: 30)"
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        default=100,
        help="Limit for validation (default: 100)"
    )
    parser.add_argument(
        "--max-batches", 
        type=int, 
        default=10,
        help="Maximum batches per run (default: 10)"
    )
    parser.add_argument(
        "--delay-min", 
        type=int, 
        default=15,
        help="Minimum delay between requests in seconds (default: 15)"
    )
    parser.add_argument(
        "--delay-max", 
        type=int, 
        default=30,
        help="Maximum delay between requests in seconds (default: 30)"
    )
    
    # SerpAPI
    parser.add_argument(
        "--enable-serpapi", 
        action="store_true",
        help="Enable SerpAPI for surgical gap-filling"
    )
    parser.add_argument(
        "--serpapi-key", 
        type=str,
        help="SerpAPI API key"
    )
    
    # Options
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Discover without saving to database"
    )
    parser.add_argument(
        "--no-validate", 
        action="store_true",
        help="Skip validation of discovered tenants"
    )
    parser.add_argument(
        "--no-sync", 
        action="store_true",
        help="Don't sync validated tenants to companies table"
    )
    parser.add_argument(
        "--stats", 
        action="store_true",
        help="Show discovery statistics and exit"
    )
    parser.add_argument(
        "-v", "--verbose", 
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    # Build config
    config = DiscoveryConfig(
        batch_size=args.batch_size,
        delay_min_seconds=args.delay_min,
        delay_max_seconds=args.delay_max,
        max_batches_per_run=args.max_batches,
        serpapi_enabled=args.enable_serpapi,
        serpapi_api_key=args.serpapi_key or os.getenv("SERPAPI_API_KEY"),
    )
    
    # Initialize engine
    engine = WorkdayTenantDiscoveryEngine(config=config)
    
    try:
        # Stats only
        if args.stats:
            print("\n📊 Workday Discovery Statistics\n")
            stats = engine.get_statistics()
            
            registry = stats.get("registry", {})
            print(f"Total tenants: {registry.get('total', 0)}")
            print(f"Active: {registry.get('active', 0)}")
            print(f"Inactive: {registry.get('inactive', 0)}")
            print(f"Pending validation: {registry.get('pending_validation', 0)}")
            print(f"Synced to companies: {registry.get('synced_to_companies', 0)}")
            
            print("\nBy shard:")
            for shard, count in registry.get("by_shard", {}).items():
                print(f"  {shard}: {count}")
            
            serpapi = stats.get("serpapi", {})
            print(f"\nSerpAPI usage today: {serpapi.get('calls_today', 0)}/{serpapi.get('daily_limit', 50)}")
            return
        
        # Import existing
        if args.import_existing:
            count = engine.import_existing_tenants()
            print(f"\n✅ Imported {count} tenants to registry")
            return
        
        # Validate existing
        if args.validate_existing:
            result = engine.validate_existing_tenants(limit=args.limit)
            print(f"\n✅ Validation complete:")
            print(f"   Checked: {result['total_checked']}")
            print(f"   Validated: {result['validated']}")
            print(f"   Failed: {result['failed']}")
            return
        
        # Discovery mode
        if not args.companies and not args.fortune500:
            parser.print_help()
            print("\n⚠️  Please specify --companies or --fortune500")
            return
        
        # Run discovery
        if args.dry_run:
            print("\n🔍 DRY RUN - No database writes\n")
        
        result = engine.run_discovery_cycle(
            company_names=args.companies,
            use_fortune500=args.fortune500,
            validate=not args.no_validate and not args.dry_run,
            sync_to_companies=not args.no_sync and not args.dry_run,
        )
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 DISCOVERY SUMMARY")
        print("=" * 50)
        print(f"Companies processed: {result.total_companies_processed}")
        print(f"Tenants discovered: {result.tenants_discovered}")
        print(f"Tenants validated: {result.tenants_validated}")
        print(f"Tenants failed: {result.tenants_failed}")
        print(f"Duration: {result.duration_seconds:.1f}s")
        
        if result.discovery_source_breakdown:
            print("\nBy source:")
            for source, count in result.discovery_source_breakdown.items():
                print(f"  {source}: {count}")
        
        if result.errors:
            print(f"\n⚠️  {len(result.errors)} errors occurred")
            if args.verbose:
                for err in result.errors[:10]:
                    print(f"   - {err}")
        
    finally:
        engine.close()


if __name__ == "__main__":
    main()
