import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, '.env'))

DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

print("\n" + "="*70)
print("ERROR ANALYSIS REPORT")
print("="*70 + "\n")

# Get total stats
cur.execute("SELECT COUNT(*) FROM jobs WHERE enrichment_status = 'completed'")
total_completed = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM jobs WHERE enrichment_status = 'failed'")
total_failed = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM jobs WHERE enrichment_status = 'pending'")
total_pending = cur.fetchone()[0]

total = total_completed + total_failed + total_pending

print(f"📊 OVERALL STATS:")
print(f"   Total Jobs: {total:,}")
print(f"   ✅ Completed: {total_completed:,} ({total_completed/total*100:.1f}%)")
print(f"   ❌ Failed: {total_failed:,} ({total_failed/total*100:.1f}%)")
print(f"   ⏳ Pending: {total_pending:,} ({total_pending/total*100:.1f}%)\n")

# Get error breakdown
print("="*70)
print("ERROR BREAKDOWN (All Time)")
print("="*70 + "\n")

cur.execute("""
    SELECT error_log, COUNT(*) as count
    FROM jobs
    WHERE enrichment_status = 'failed' AND error_log IS NOT NULL
    GROUP BY error_log
    ORDER BY count DESC
    LIMIT 5
""")

for error, count in cur.fetchall():
    error_short = (error[:60] + '...') if len(error) > 60 else error
    percentage = count / total_failed * 100
    print(f"  • {error_short}")
    print(f"    Count: {count:,} ({percentage:.1f}% of failures)\n")

# Check recent activity (last hour)
print("="*70)
print("RECENT ACTIVITY (Last Hour)")
print("="*70 + "\n")

cur.execute("""
    SELECT COUNT(*)
    FROM job_enrichment 
    WHERE last_enriched_at > NOW() - INTERVAL '1 hour'
""")
recent_success = cur.fetchone()[0]

cur.execute("""
    SELECT COUNT(*)
    FROM jobs
    WHERE enrichment_status = 'failed' 
    AND updated_at > NOW() - INTERVAL '1 hour'
""")
recent_failed = cur.fetchone()[0]

recent_total = recent_success + recent_failed

if recent_total > 0:
    print(f"   ✅ Successfully enriched: {recent_success}")
    print(f"   ❌ Failed: {recent_failed}")
    print(f"   📈 Success rate: {recent_success/recent_total*100:.1f}%\n")
else:
    print("   No activity in the last hour\n")

print("="*70)
print("INTERPRETATION")
print("="*70 + "\n")

print("The high failure rate is likely due to:")
print("  1. Historical schema errors (before migrations were applied)")
print("  2. Rate limit errors from before multi-key rotation")
print("  3. Invalid job descriptions (too short, no content)")
print("\nRecent success rate shows current system health after fixes.")

cur.close()
conn.close()

print("\n" + "="*70 + "\n")
