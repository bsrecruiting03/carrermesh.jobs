#!/usr/bin/env python3
"""
Real-time Enrichment Monitoring Dashboard
Displays live statistics about the job enrichment pipeline
"""

import psycopg2
import os
import sys
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, '.env'))

DATABASE_URL = os.getenv("DATABASE_URL")

# ANSI color codes
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
CYAN = '\033[96m'
RESET = '\033[0m'
BOLD = '\033[1m'

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_progress_bar(percentage, width=50):
    """Draw a progress bar"""
    filled = int(width * percentage / 100)
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}] {percentage:.1f}%"

def get_stats(conn):
    """Fetch enrichment statistics from database"""
    cur = conn.cursor()
    
    # Total counts
    cur.execute("SELECT COUNT(*) FROM jobs")
    total_jobs = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM jobs WHERE enrichment_status = 'completed'")
    completed = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM jobs WHERE enrichment_status = 'failed'")
    failed = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM jobs WHERE enrichment_status = 'pending'")
    pending = cur.fetchone()[0]
    
    # Recent activity (last hour)
    cur.execute("""
        SELECT COUNT(*) 
        FROM job_enrichment 
        WHERE last_enriched_at > NOW() - INTERVAL '1 hour'
    """)
    last_hour = cur.fetchone()[0] or 0
    
    # Recent activity (last 5 minutes)
    cur.execute("""
        SELECT COUNT(*) 
        FROM job_enrichment 
        WHERE last_enriched_at > NOW() - INTERVAL '5 minutes'
    """)
    last_5min = cur.fetchone()[0] or 0
    
    # Sample recent enrichments
    cur.execute("""
        SELECT 
            je.job_id,
            j.title,
            j.company,
            je.tech_languages,
            je.visa_sponsorship->>'mentioned' as visa,
            je.last_enriched_at
        FROM job_enrichment je
        JOIN jobs j ON je.job_id = j.job_id
        ORDER BY je.last_enriched_at DESC
        LIMIT 5
    """)
    recent_jobs = cur.fetchall()
    
    # Error breakdown (if any)
    cur.execute("""
        SELECT error_log, COUNT(*) 
        FROM jobs 
        WHERE enrichment_status = 'failed' AND error_log IS NOT NULL
        GROUP BY error_log
        ORDER BY COUNT(*) DESC
        LIMIT 3
    """)
    errors = cur.fetchall()
    
    cur.close()
    
    return {
        'total': total_jobs,
        'completed': completed,
        'failed': failed,
        'pending': pending,
        'last_hour': last_hour,
        'last_5min': last_5min,
        'recent_jobs': recent_jobs,
        'errors': errors
    }

def display_dashboard(stats):
    """Display the monitoring dashboard"""
    clear_screen()
    
    # Header
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}    JOB ENRICHMENT MONITORING DASHBOARD{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")
    print(f"  Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Overall Progress
    total = stats['total']
    completed = stats['completed']
    failed = stats['failed']
    pending = stats['pending']
    
    completion_pct = (completed / total * 100) if total > 0 else 0
    
    print(f"{BOLD}📊 OVERALL PROGRESS{RESET}")
    print(f"  {draw_progress_bar(completion_pct)}")
    print(f"\n  Total Jobs:      {total:,}")
    print(f"  {GREEN}✓ Completed:{RESET}     {completed:,} ({completion_pct:.2f}%)")
    print(f"  {RED}✗ Failed:{RESET}        {failed:,} ({failed/total*100:.2f}%)")
    print(f"  {YELLOW}⏳ Pending:{RESET}       {pending:,} ({pending/total*100:.2f}%)")
    
    # Processing Rate
    print(f"\n{BOLD}⚡ PROCESSING RATE{RESET}")
    print(f"  Last 5 minutes:  {GREEN}{stats['last_5min']}{RESET} jobs ({stats['last_5min']/5:.1f}/min)")
    print(f"  Last hour:       {GREEN}{stats['last_hour']}{RESET} jobs ({stats['last_hour']/60:.1f}/min)")
    
    if stats['last_hour'] > 0:
        est_hours = pending / (stats['last_hour']) if stats['last_hour'] > 0 else 0
        print(f"  {BLUE}Est. completion:{RESET} {est_hours:.1f} hours")
    
    # Recent Jobs
    if stats['recent_jobs']:
        print(f"\n{BOLD}🔍 RECENTLY ENRICHED (Last 5){RESET}")
        for job in stats['recent_jobs']:
            job_id, title, company, langs, visa, enriched_at = job
            title_short = (title[:40] + '...') if title and len(title) > 40 else title
            langs_display = langs[:30] if langs else 'N/A'
            visa_display = f"{GREEN}✓{RESET}" if visa == 'true' else f"{RED}✗{RESET}"
            time_ago = (datetime.now() - enriched_at).total_seconds() if enriched_at else 0
            time_str = f"{int(time_ago)}s ago" if time_ago < 60 else f"{int(time_ago/60)}m ago"
            
            print(f"  • {title_short}")
            print(f"    {company} | Langs: {langs_display} | Visa: {visa_display} | {time_str}")
    
    # Errors
    if stats['errors']:
        print(f"\n{BOLD}{RED}⚠️  TOP ERRORS{RESET}")
        for error, count in stats['errors']:
            error_short = (error[:60] + '...') if error and len(error) > 60 else error
            print(f"  • {error_short} ({count} times)")
    
    print(f"\n{CYAN}{'='*80}{RESET}")
    print(f"  Press Ctrl+C to exit | Auto-refresh every 5 seconds")
    print(f"{CYAN}{'='*80}{RESET}\n")

def main():
    """Main monitoring loop"""
    print("Starting Enrichment Monitor...")
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        
        while True:
            try:
                stats = get_stats(conn)
                display_dashboard(stats)
                time.sleep(5)  # Refresh every 5 seconds
                
            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"{RED}Error fetching stats: {e}{RESET}")
                time.sleep(5)
                
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Monitoring stopped.{RESET}\n")
        sys.exit(0)
    except Exception as e:
        print(f"{RED}Fatal error: {e}{RESET}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
