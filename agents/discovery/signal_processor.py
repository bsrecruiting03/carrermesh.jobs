"""
MultiATSSignalProcessor - Signal-Based Discovery Engine

Extends WorkdaySignalProcessor to support:
- Workday (API-first)
- Oracle/Taleo (HTML-first)
- iCIMS (URL-structure-first)

CRITICAL: This processor NEVER modifies job content.
It only:
1. READS from raw_jobs and jobs tables
2. WRITES to domain_graph (new signals)
3. PUSHES to Redis discovery queues
4. SETS a flag (workday_signal_scanned = true)

ALL CHANGES ARE ADDITIVE. NO EXISTING DATA IS MODIFIED.
"""

import os
import sys
import re
import json
import logging
from urllib.parse import urlparse, parse_qs
from datetime import datetime

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import psycopg2
from psycopg2.extras import execute_batch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MultiATSSignalProcessor")

DATABASE_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

# Redis (with fallback)
try:
    from us_ats_jobs.queue.redis_manager import RedisQueueManager
    redis_manager = RedisQueueManager()
    REDIS_AVAILABLE = redis_manager.client is not None
except Exception as e:
    logger.warning(f"Redis not available, using Postgres fallback: {e}")
    REDIS_AVAILABLE = False

# =============================================================================
# URL EXTRACTION & NORMALIZATION (SHARED)
# =============================================================================

URL_REGEX = re.compile(r'https?://[^\s<>"\']+|www\.[^\s<>"\']+', re.IGNORECASE)

def extract_all_urls(content: str) -> list:
    """Extract all URLs from HTML/JSON/text content."""
    if not content:
        return []
    
    if isinstance(content, dict):
        content = json.dumps(content)
    
    return URL_REGEX.findall(str(content))

def normalize_url(url: str) -> str:
    """Normalize URL for deduplication."""
    url = url.strip().rstrip('/')
    if url.startswith('www.'):
        url = 'https://' + url
    return url

def get_domain(url: str) -> str:
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except:
        return url

# =============================================================================
# WORKDAY DETECTION
# =============================================================================

WORKDAY_PATTERNS = [
    r'myworkdayjobs\.com',
    r'\.wd\d+\.myworkdayjobs\.com',
    r'/wday/cxs/',
    r'workday\.com/.*careers',
]

def is_workday_url(url: str) -> bool:
    """Check if URL is a Workday endpoint."""
    url_lower = url.lower()
    for pattern in WORKDAY_PATTERNS:
        if re.search(pattern, url_lower):
            return True
    return False

def extract_workday_embeds(content: str) -> set:
    """Extract embedded Workday configurations from HTML/JS."""
    candidates = set()
    if not content:
        return candidates
    
    content_str = str(content)
    
    # Pattern 1: Direct Workday domain references
    workday_urls = re.findall(r'[a-zA-Z0-9-]+\.wd\d*\.?myworkdayjobs\.com', content_str)
    for url in workday_urls:
        candidates.add(f"https://{url}")
    
    # Pattern 2: Workday API endpoints
    api_refs = re.findall(r'/wday/cxs/[^/\s"\']+', content_str)
    for ref in api_refs:
        candidates.add(ref)
    
    return candidates

def normalize_workday_endpoint(url: str) -> str:
    """
    Normalize Workday URL to canonical endpoint.
    Example: https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite
    """
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    
    if 'myworkdayjobs.com' not in host:
        return url
    
    # Extract tenant and path
    path_parts = parsed.path.strip('/').split('/')
    site_path = path_parts[0] if path_parts else 'External'
    
    # Skip job-specific paths
    if site_path.lower() in ['job', 'jobs', 'wday', 'cxs']:
        site_path = path_parts[1] if len(path_parts) > 1 else 'External'
    
    return f"https://{host}/{site_path}"

# =============================================================================
# ORACLE/TALEO DETECTION
# =============================================================================

ORACLE_PATTERNS = [
    r'oraclecloud\.com',
    r'taleo\.net',
    r'tal\.net',           # For TalentLink (Goldman Sachs, etc)
    r'oracle\.com',        # Legacy Oracle matches
    r'/careersection/',
    r'careersectionid=',
    r'hcmUI/CandidateExperience',
]

ORACLE_HTML_MARKERS = [
    'ORACLE_HCM',
    'Taleo',
    'careerSection',
    'requisitionList',
]

def is_oracle_url(url: str) -> bool:
    """Check if URL is an Oracle/Taleo endpoint."""
    url_lower = url.lower()
    
    for pattern in ORACLE_PATTERNS:
        if re.search(pattern, url_lower):
            return True
    
    return False

def extract_oracle_embeds(content: str) -> set:
    """Extract embedded Oracle/Taleo configurations from HTML/JS."""
    candidates = set()
    if not content:
        return candidates
    
    content_str = str(content)
    
    # Pattern 1: Oracle Cloud domains
    oracle_urls = re.findall(r'[a-zA-Z0-9-]+\.fa\.[a-zA-Z0-9]+\.oraclecloud\.com', content_str)
    for url in oracle_urls:
        candidates.add(f"https://{url}")
    
    # Pattern 2: Taleo domains
    taleo_urls = re.findall(r'[a-zA-Z0-9-]+\.taleo\.net', content_str)
    for url in taleo_urls:
        candidates.add(f"https://{url}")
    
    # Pattern 3: CareerSection URLs
    cs_urls = re.findall(r'https?://[^"\s]+/careersection/\d+/[^"\s]+', content_str)
    for url in cs_urls:
        candidates.add(url)
    
    return candidates

def normalize_oracle_endpoint(url: str) -> str:
    """
    Normalize Oracle URL to career section root.
    
    Input: https://company.taleo.net/careersection/2/jobdetail.ftl?job=12345
    Output: https://company.taleo.net/careersection/2/jobsearch.ftl
    
    Rejects:
    - URLs with only job= parameter
    - Session-only URLs (;jsessionid=)
    - Tracking parameters
    """
    # Remove session IDs
    url = re.sub(r';jsessionid=[^?&]+', '', url)
    
    parsed = urlparse(url)
    
    # Oracle HCM Cloud
    if 'oraclecloud.com' in parsed.netloc:
        # Normalize to CandidateExperience root
        path = parsed.path
        if '/hcmUI/CandidateExperience' in path:
            base = path.split('/hcmUI/CandidateExperience')[0]
            return f"https://{parsed.netloc}{base}/hcmUI/CandidateExperience"
        return f"https://{parsed.netloc}"
    
    # Taleo Enterprise
    if '/careersection/' in parsed.path:
        # Extract career section ID
        cs_match = re.search(r'/careersection/(\d+|[\w-]+)/', parsed.path)
        if cs_match:
            cs_id = cs_match.group(1)
            return f"https://{parsed.netloc}/careersection/{cs_id}/jobsearch.ftl"
    
    return f"https://{parsed.netloc}"

# =============================================================================
# iCIMS DETECTION
# =============================================================================

ICIMS_PATTERNS = [
    r'icims\.com',
    r'careers-[a-zA-Z0-9-]+\.icims\.com',
]

def is_icims_url(url: str) -> bool:
    """Check if URL is an iCIMS endpoint."""
    url_lower = url.lower()
    
    if 'icims.com' not in url_lower:
        return False
    
    # Must have /jobs/ path for job listings
    if '/jobs/' in url_lower or '/jobs' in url_lower:
        return True
    
    return False

def extract_icims_embeds(content: str) -> set:
    """Extract embedded iCIMS configurations from HTML/JS."""
    candidates = set()
    if not content:
        return candidates
    
    content_str = str(content)
    
    # Pattern: iCIMS career domains
    icims_urls = re.findall(r'careers-[a-zA-Z0-9-]+\.icims\.com', content_str)
    for url in icims_urls:
        candidates.add(f"https://{url}")
    
    # Pattern: Direct iCIMS job URLs
    job_urls = re.findall(r'https?://[^"\s]+\.icims\.com/jobs/\d+', content_str)
    for url in job_urls:
        candidates.add(url)
    
    return candidates

def normalize_icims_endpoint(url: str) -> str:
    """
    Normalize iCIMS URL to career portal root.
    
    Input: https://careers-company.icims.com/jobs/1234/senior-engineer
    Output: https://careers-company.icims.com
    """
    parsed = urlparse(url)
    return f"https://{parsed.netloc}"

# =============================================================================
# ATS HINT DETECTION (SHARED)
# =============================================================================

def detect_ats_hint(url: str) -> str:
    """Identify ATS provider from URL pattern."""
    url_lower = url.lower()
    
    if 'myworkdayjobs.com' in url_lower or '/wday/' in url_lower:
        return 'workday'
    elif 'greenhouse.io' in url_lower or 'boards.greenhouse.io' in url_lower:
        return 'greenhouse'
    elif 'lever.co' in url_lower or 'jobs.lever.co' in url_lower:
        return 'lever'
    elif 'ashbyhq.com' in url_lower:
        return 'ashby'
    elif 'icims.com' in url_lower:
        return 'icims'
    elif 'taleo.net' in url_lower or 'oraclecloud.com' in url_lower:
        return 'oracle'
    elif 'jobvite.com' in url_lower:
        return 'jobvite'
    elif 'bamboohr.com' in url_lower:
        return 'bamboohr'
    elif 'workable.com' in url_lower:
        return 'workable'
    
    return None

# =============================================================================
# CORE MULTI-ATS SIGNAL PROCESSOR
# =============================================================================

class MultiATSSignalProcessor:
    """
    Unified signal processor for Workday, Oracle, and iCIMS discovery.
    
    Extends the original WorkdaySignalProcessor to detect signals from
    multiple ATS providers in a single pass through raw_jobs.
    """
    
    def __init__(self):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.stats = {
            'jobs_scanned': 0,
            'urls_extracted': 0,
            'domains_logged': 0,
            'workday_candidates': 0,
            'oracle_candidates': 0,
            'icims_candidates': 0,
            'embeds_found': 0
        }
    
    def run(self, batch_size: int = 500, max_batches: int = None):
        """
        Main processing loop.
        Scans unprocessed raw_jobs, extracts signals for all ATS types.
        """
        logger.info(f"🚀 Starting MultiATSSignalProcessor (batch_size={batch_size})...")
        
        batch_count = 0
        
        while True:
            jobs = self._fetch_unprocessed_batch(batch_size)
            
            if not jobs:
                logger.info("✅ No more unprocessed jobs. Exiting.")
                break
            
            logger.info(f"📦 Processing batch {batch_count + 1}: {len(jobs)} jobs...")
            
            for job in jobs:
                self._process_job(job)
            
            batch_count += 1
            
            if max_batches and batch_count >= max_batches:
                logger.info(f"🛑 Reached max_batches limit ({max_batches}). Stopping.")
                break
        
        self._report_stats()
    
    def _fetch_unprocessed_batch(self, limit: int) -> list:
        """Fetch raw_jobs that haven't been scanned."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT r.job_id, r.raw_payload, j.job_description
            FROM raw_jobs r
            LEFT JOIN jobs j ON r.job_id = j.job_id
            WHERE r.workday_signal_scanned = FALSE
            LIMIT %s
        """, (limit,))
        
        rows = cur.fetchall()
        return [
            {'job_id': row[0], 'raw_payload': row[1], 'job_description': row[2]}
            for row in rows
        ]
    
    def _process_job(self, job: dict):
        """Process a single job record for all ATS types."""
        workday_candidates = set()
        oracle_candidates = set()
        icims_candidates = set()
        all_urls = []
        
        # Step 1: Extract URLs from raw_payload
        raw_content = job.get('raw_payload')
        if raw_content:
            urls = extract_all_urls(raw_content)
            all_urls.extend(urls)
        
        # Step 2: Extract URLs from job_description
        desc = job.get('job_description')
        if desc:
            urls = extract_all_urls(desc)
            all_urls.extend(urls)
        
        self.stats['urls_extracted'] += len(all_urls)
        
        # Step 3: Classify and log URLs
        for url in all_urls:
            normalized = normalize_url(url)
            domain = get_domain(normalized)
            ats_hint = detect_ats_hint(normalized)
            
            # Log to domain_graph (NON-DESTRUCTIVE)
            self._log_domain(job['job_id'], url, domain, ats_hint)
            
            # Classify by ATS type
            if is_workday_url(normalized):
                endpoint = normalize_workday_endpoint(normalized)
                workday_candidates.add(endpoint)
            
            if is_oracle_url(normalized):
                endpoint = normalize_oracle_endpoint(normalized)
                oracle_candidates.add(endpoint)
            
            if is_icims_url(normalized):
                endpoint = normalize_icims_endpoint(normalized)
                icims_candidates.add(endpoint)
        
        # Step 4: Extract embedded configs
        if raw_content:
            # Workday embeds
            wd_embeds = extract_workday_embeds(raw_content)
            for embed in wd_embeds:
                workday_candidates.add(normalize_workday_endpoint(embed))
            
            # Oracle embeds
            oracle_embeds = extract_oracle_embeds(raw_content)
            for embed in oracle_embeds:
                oracle_candidates.add(normalize_oracle_endpoint(embed))
            
            # iCIMS embeds
            icims_embeds = extract_icims_embeds(raw_content)
            for embed in icims_embeds:
                icims_candidates.add(normalize_icims_endpoint(embed))
            
            self.stats['embeds_found'] += len(wd_embeds) + len(oracle_embeds) + len(icims_embeds)
        
        # Step 5: Emit candidates to appropriate queues
        for candidate in workday_candidates:
            self._emit_candidate(candidate, job['job_id'], 'workday')
        
        for candidate in oracle_candidates:
            self._emit_candidate(candidate, job['job_id'], 'oracle')
        
        for candidate in icims_candidates:
            self._emit_candidate(candidate, job['job_id'], 'icims')
        
        self.stats['workday_candidates'] += len(workday_candidates)
        self.stats['oracle_candidates'] += len(oracle_candidates)
        self.stats['icims_candidates'] += len(icims_candidates)
        
        # Step 6: Mark as scanned (SAFE FLAG ONLY)
        self._mark_scanned(job['job_id'])
        
        self.stats['jobs_scanned'] += 1
    
    def _log_domain(self, job_id: str, raw_url: str, domain: str, ats_hint: str):
        """Log domain to domain_graph table."""
        try:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO domain_graph (source_job_id, raw_url, normalized_domain, ats_hint)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (source_job_id, raw_url) DO NOTHING
            """, (job_id, raw_url[:2000], domain[:500], ats_hint))
            self.conn.commit()
            self.stats['domains_logged'] += 1
        except Exception as e:
            self.conn.rollback()
    
    def _emit_candidate(self, url: str, source_job_id: str, ats_type: str):
        """Emit candidate to Redis queue (or Postgres fallback)."""
        payload = {
            "url": url,
            "ats_type": ats_type,
            "source": "raw_job_signal",
            "job_id": source_job_id,
            "confidence_hint": 0.4,
            "discovered_at": datetime.now().isoformat()
        }
        
        queue_name = f"queue:discovery:{ats_type}_candidates"
        
        if REDIS_AVAILABLE:
            try:
                redis_manager.client.rpush(queue_name, json.dumps(payload))
                return
            except Exception as e:
                logger.warning(f"Redis push failed, using fallback: {e}")
        
        # Postgres fallback
        self._postgres_fallback(payload, ats_type)
    
    def _postgres_fallback(self, payload: dict, ats_type: str):
        """Fallback: Store discovery candidate in Postgres."""
        try:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO pending_discovery (url, source, source_job_id, confidence, payload, ats_type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (url) DO NOTHING
            """, (
                payload['url'],
                payload['source'],
                payload['job_id'],
                payload['confidence_hint'],
                json.dumps(payload),
                ats_type
            ))
            self.conn.commit()
        except psycopg2.errors.UndefinedTable:
            self.conn.rollback()
            self._create_fallback_table()
            self._postgres_fallback(payload, ats_type)
        except psycopg2.errors.UndefinedColumn:
            # ats_type column doesn't exist, add it
            self.conn.rollback()
            self._add_ats_type_column()
            self._postgres_fallback(payload, ats_type)
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Fallback insert failed: {e}")
    
    def _create_fallback_table(self):
        """Create pending_discovery table for Redis fallback."""
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pending_discovery (
                id SERIAL PRIMARY KEY,
                url TEXT UNIQUE,
                source TEXT,
                source_job_id TEXT,
                confidence FLOAT,
                payload JSONB,
                ats_type TEXT DEFAULT 'workday',
                processed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_pending_discovery_processed ON pending_discovery(processed);
            CREATE INDEX IF NOT EXISTS idx_pending_discovery_ats_type ON pending_discovery(ats_type);
        """)
        self.conn.commit()
        logger.info("✅ Created pending_discovery fallback table")
    
    def _add_ats_type_column(self):
        """Add ats_type column to existing pending_discovery table."""
        cur = self.conn.cursor()
        cur.execute("""
            ALTER TABLE pending_discovery ADD COLUMN IF NOT EXISTS ats_type TEXT DEFAULT 'workday';
            CREATE INDEX IF NOT EXISTS idx_pending_discovery_ats_type ON pending_discovery(ats_type);
        """)
        self.conn.commit()
        logger.info("✅ Added ats_type column to pending_discovery")
    
    def _mark_scanned(self, job_id: str):
        """Mark raw_job as scanned (SAFE FLAG ONLY)."""
        cur = self.conn.cursor()
        cur.execute("""
            UPDATE raw_jobs SET workday_signal_scanned = TRUE WHERE job_id = %s
        """, (job_id,))
        self.conn.commit()
    
    def _report_stats(self):
        """Report processing statistics."""
        logger.info("=" * 60)
        logger.info("📊 Multi-ATS Signal Processing Complete - Statistics:")
        logger.info(f"   Jobs Scanned: {self.stats['jobs_scanned']}")
        logger.info(f"   URLs Extracted: {self.stats['urls_extracted']}")
        logger.info(f"   Domains Logged: {self.stats['domains_logged']}")
        logger.info(f"   Workday Candidates: {self.stats['workday_candidates']}")
        logger.info(f"   Oracle Candidates: {self.stats['oracle_candidates']}")
        logger.info(f"   iCIMS Candidates: {self.stats['icims_candidates']}")
        logger.info(f"   Embedded Configs: {self.stats['embeds_found']}")
        logger.info("=" * 60)
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# Backwards compatibility alias
WorkdaySignalProcessor = MultiATSSignalProcessor


def main():
    """Entry point for CLI execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-ATS Signal Processor')
    parser.add_argument('--batch-size', type=int, default=500, help='Jobs per batch')
    parser.add_argument('--max-batches', type=int, default=None, help='Max batches (None = all)')
    args = parser.parse_args()
    
    processor = MultiATSSignalProcessor()
    try:
        processor.run(batch_size=args.batch_size, max_batches=args.max_batches)
    finally:
        processor.close()


if __name__ == "__main__":
    main()
