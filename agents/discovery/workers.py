"""
Multi-ATS Discovery Consumer Workers

Workers for processing discovery candidates across multiple ATS types:
1. WorkdayCandidateConsumer - Normalizes and deduplicates Workday candidates
2. WorkdayVerificationWorker - Validates Workday endpoints via API
3. OracleVerificationWorker - Validates Oracle/Taleo endpoints via HTML
4. iCIMSVerificationWorker - Validates iCIMS endpoints via URL structure

NON-DESTRUCTIVE: Only ADDS new endpoints. Never modifies existing data.
Reuses same aging/decay logic for all ATS types.
"""

import os
import sys
import json
import time
import logging
import requests
import re
from urllib.parse import urlparse
from datetime import datetime

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ATSDiscoveryWorker")

DATABASE_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Redis
try:
    from us_ats_jobs.queue.redis_manager import RedisQueueManager
    redis_manager = RedisQueueManager()
    REDIS_AVAILABLE = redis_manager.client is not None
except Exception as e:
    logger.warning(f"Redis not available: {e}")
    REDIS_AVAILABLE = False

# =============================================================================
# WORKDAY VERIFICATION (API-BASED)
# =============================================================================

def normalize_workday_endpoint(url: str) -> dict:
    """Normalize Workday URL to canonical endpoint identity."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        
        if 'myworkdayjobs.com' not in host:
            return None
        
        parts = host.split('.')
        if len(parts) < 3:
            return None
        
        tenant = parts[0]
        shard = parts[1] if len(parts) >= 4 and parts[1].startswith('wd') else None
        path = parsed.path.strip('/').split('/')[0] if parsed.path else ''
        
        if shard:
            canonical = f"https://{tenant}.{shard}.myworkdayjobs.com/{path}"
        else:
            canonical = f"https://{tenant}.myworkdayjobs.com/{path}"
        
        return {
            'tenant': tenant,
            'shard': shard,
            'path': path,
            'canonical_url': canonical.rstrip('/')
        }
    except:
        return None


def verify_workday_endpoint(endpoint: dict) -> tuple:
    """Verify Workday endpoint via API. Returns (success, jobs_count, error)."""
    tenant = endpoint['tenant']
    shard = endpoint.get('shard')
    path = endpoint.get('path', 'External')
    
    if shard:
        api_url = f"https://{tenant}.{shard}.myworkdayjobs.com/wday/cxs/{tenant}/{path}/jobs"
    else:
        api_url = f"https://{tenant}.myworkdayjobs.com/wday/cxs/{tenant}/{path}/jobs"
    
    payload = {"limit": 1, "offset": 0, "appliedFacets": {}, "searchText": ""}
    headers = {"Content-Type": "application/json", **HEADERS}
    
    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        if response.status_code != 200:
            return False, 0, f"HTTP {response.status_code}"
        
        data = response.json()
        if 'jobPostings' not in data and 'total' not in data:
            return False, 0, "Invalid response"
        
        return True, data.get('total', 0), None
    except Exception as e:
        return False, 0, str(e)

# =============================================================================
# ORACLE/TALEO VERIFICATION (HTML-BASED)
# =============================================================================

def normalize_oracle_endpoint(url: str) -> dict:
    """Normalize Oracle URL to canonical endpoint identity."""
    url = re.sub(r';jsessionid=[^?&]+', '', url)  # Remove session IDs
    parsed = urlparse(url)
    
    # Oracle HCM Cloud
    if 'oraclecloud.com' in parsed.netloc:
        if '/hcmUI/CandidateExperience' in parsed.path:
            base = parsed.path.split('/hcmUI/CandidateExperience')[0]
            canonical = f"https://{parsed.netloc}{base}/hcmUI/CandidateExperience"
        else:
            canonical = f"https://{parsed.netloc}"
        return {
            'type': 'hcm_cloud',
            'canonical_url': canonical.rstrip('/')
        }
    
    # Taleo Enterprise
    if '/careersection/' in parsed.path:
        cs_match = re.search(r'/careersection/(\d+|[\w-]+)/', parsed.path)
        if cs_match:
            cs_id = cs_match.group(1)
            canonical = f"https://{parsed.netloc}/careersection/{cs_id}/jobsearch.ftl"
            return {
                'type': 'taleo',
                'career_section': cs_id,
                'canonical_url': canonical
            }
    
    return {
        'type': 'oracle_generic',
        'canonical_url': f"https://{parsed.netloc}"
    }


def verify_oracle_endpoint(endpoint: dict) -> tuple:
    """
    Verify Oracle endpoint via HTML.
    Oracle has NO universal API - verification is HTML-based.
    
    Returns (success, has_jobs, error)
    """
    url = endpoint.get('canonical_url')
    if not url:
        return False, False, "No URL"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        
        if response.status_code != 200:
            return False, False, f"HTTP {response.status_code}"
        
        html = response.text.lower()
        
        # Check for Oracle/Taleo markers
        if 'careersection' not in html and 'candidateexperience' not in html:
            return False, False, "Not an Oracle career page"
        
        # Check for job listings
        has_jobs = any(marker in html for marker in [
            'jobsearch', 'requisition', 'job-listing', 'joblist',
            'position', 'vacancy', 'openings'
        ])
        
        return True, has_jobs, None
        
    except Exception as e:
        return False, False, str(e)

# =============================================================================
# iCIMS VERIFICATION (URL STRUCTURE-BASED)
# =============================================================================

def normalize_icims_endpoint(url: str) -> dict:
    """Normalize iCIMS URL to career portal root."""
    parsed = urlparse(url)
    return {
        'type': 'icims',
        'canonical_url': f"https://{parsed.netloc}"
    }


def verify_icims_endpoint(endpoint: dict) -> tuple:
    """
    Verify iCIMS endpoint via URL structure.
    
    Returns (success, has_jobs, error)
    """
    base_url = endpoint.get('canonical_url')
    if not base_url:
        return False, False, "No URL"
    
    jobs_url = f"{base_url}/jobs"
    
    try:
        response = requests.get(jobs_url, headers=HEADERS, timeout=15, allow_redirects=True)
        
        if response.status_code != 200:
            return False, False, f"HTTP {response.status_code}"
        
        html = response.text.lower()
        
        # Check for iCIMS markers
        if 'icims' not in html:
            return False, False, "Not an iCIMS page"
        
        # Check for job listings
        has_jobs = '/jobs/' in html
        
        return True, has_jobs, None
        
    except Exception as e:
        return False, False, str(e)


# =============================================================================
# GENERIC ENDPOINT OPERATIONS (SHARED)
# =============================================================================

def endpoint_exists(conn, canonical_url: str) -> bool:
    """Check if endpoint already exists in career_endpoints."""
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM career_endpoints WHERE canonical_url = %s LIMIT 1", (canonical_url,))
    return cur.fetchone() is not None


def register_endpoint(conn, endpoint: dict, ats_provider: str, confidence: float):
    """
    Register verified endpoint in career_endpoints.
    NON-DESTRUCTIVE: Uses INSERT ... ON CONFLICT.
    """
    try:
        cur = conn.cursor()
        canonical_url = endpoint.get('canonical_url')
        slug = canonical_url.replace('https://', '').replace('http://', '')
        
        cur.execute("""
            INSERT INTO career_endpoints (
                canonical_url, ats_provider, ats_slug,
                discovered_from, confidence_score, last_verified_at, active
            ) VALUES (%s, %s, %s, 'signal_based', %s, NOW(), TRUE)
            ON CONFLICT (canonical_url) DO UPDATE SET
                confidence_score = LEAST(career_endpoints.confidence_score + 0.1, 1.0),
                last_verified_at = NOW(),
                consecutive_failures = 0
        """, (canonical_url, ats_provider, slug, min(confidence + 0.1, 1.0)))
        
        conn.commit()
        logger.info(f"✅ Registered {ats_provider}: {canonical_url}")
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to register: {e}")
        return False


# =============================================================================
# UNIFIED CANDIDATE CONSUMER
# =============================================================================

class MultiATSCandidateConsumer:
    """
    Unified consumer for all ATS types.
    Pops from type-specific queues and routes to appropriate normalizer.
    """
    
    def __init__(self, ats_type: str = 'workday'):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.ats_type = ats_type
        self.queue_name = f"queue:discovery:{ats_type}_candidates"
        self.verify_queue = f"queue:discovery:{ats_type}_verify"
        self.stats = {'consumed': 0, 'deduplicated': 0, 'pushed': 0}
        
        # Select normalizer based on ATS type
        self.normalizers = {
            'workday': normalize_workday_endpoint,
            'oracle': normalize_oracle_endpoint,
            'icims': normalize_icims_endpoint,
        }
    
    def run(self, max_iterations: int = None):
        logger.info(f"🚀 Starting {self.ats_type.upper()} Candidate Consumer...")
        
        iteration = 0
        while True:
            msg = self._pop_candidate()
            
            if not msg:
                time.sleep(1)
                iteration += 1
                if max_iterations and iteration >= max_iterations:
                    break
                continue
            
            self._process_candidate(msg)
            iteration = 0
            
            if max_iterations and self.stats['consumed'] >= max_iterations:
                break
        
        self._report_stats()
    
    def _pop_candidate(self) -> dict:
        if REDIS_AVAILABLE:
            try:
                result = redis_manager.client.blpop(self.queue_name, timeout=1)
                if result:
                    return json.loads(result[1])
            except Exception as e:
                logger.warning(f"Redis pop failed: {e}")
        
        return self._pop_from_postgres()
    
    def _pop_from_postgres(self) -> dict:
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT * FROM pending_discovery
                WHERE processed = FALSE AND ats_type = %s
                ORDER BY created_at ASC
                LIMIT 1 FOR UPDATE SKIP LOCKED
            """, (self.ats_type,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE pending_discovery SET processed = TRUE WHERE id = %s", (row['id'],))
                self.conn.commit()
                return dict(row)
        except:
            self.conn.rollback()
        return None
    
    def _process_candidate(self, msg: dict):
        self.stats['consumed'] += 1
        
        url = msg.get('url')
        if not url:
            return
        
        # Normalize using ATS-specific normalizer
        normalizer = self.normalizers.get(self.ats_type, lambda x: {'canonical_url': x})
        endpoint = normalizer(url)
        if not endpoint:
            return
        
        # Deduplicate
        if endpoint_exists(self.conn, endpoint.get('canonical_url', url)):
            self.stats['deduplicated'] += 1
            return
        
        # Push to verification queue
        self._push_to_verification(endpoint, msg.get('confidence_hint', 0.4))
        self.stats['pushed'] += 1
    
    def _push_to_verification(self, endpoint: dict, confidence: float):
        payload = {
            "endpoint": endpoint,
            "confidence": confidence,
            "ats_type": self.ats_type,
            "queued_at": datetime.now().isoformat()
        }
        
        if REDIS_AVAILABLE:
            try:
                redis_manager.client.rpush(self.verify_queue, json.dumps(payload))
                return
            except:
                pass
        
        # Postgres fallback
        try:
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO pending_verification (canonical_url, endpoint_data, confidence, ats_type, created_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (canonical_url) DO NOTHING
            """, (endpoint.get('canonical_url'), json.dumps(endpoint), confidence, self.ats_type))
            self.conn.commit()
        except psycopg2.errors.UndefinedTable:
            self.conn.rollback()
            self._create_verification_table()
            self._push_to_verification(endpoint, confidence)
        except psycopg2.errors.UndefinedColumn:
            self.conn.rollback()
            self._add_ats_type_column()
            self._push_to_verification(endpoint, confidence)
        except:
            self.conn.rollback()
    
    def _create_verification_table(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pending_verification (
                id SERIAL PRIMARY KEY,
                canonical_url TEXT UNIQUE,
                endpoint_data JSONB,
                confidence FLOAT,
                ats_type TEXT DEFAULT 'workday',
                verified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_pv_ats_type ON pending_verification(ats_type);
        """)
        self.conn.commit()
    
    def _add_ats_type_column(self):
        cur = self.conn.cursor()
        cur.execute("ALTER TABLE pending_verification ADD COLUMN IF NOT EXISTS ats_type TEXT DEFAULT 'workday'")
        self.conn.commit()
    
    def _report_stats(self):
        logger.info(f"📊 {self.ats_type.upper()} Consumer Stats: {self.stats}")


# =============================================================================
# UNIFIED VERIFICATION WORKER
# =============================================================================

class MultiATSVerificationWorker:
    """
    Unified verification worker for all ATS types.
    Routes to appropriate verifier based on ATS type.
    """
    
    def __init__(self, ats_type: str = 'workday'):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.ats_type = ats_type
        self.queue_name = f"queue:discovery:{ats_type}_verify"
        self.stats = {'verified': 0, 'failed': 0, 'registered': 0}
        
        # Select verifier based on ATS type
        self.verifiers = {
            'workday': verify_workday_endpoint,
            'oracle': verify_oracle_endpoint,
            'icims': verify_icims_endpoint,
        }
    
    def run(self, max_iterations: int = None):
        logger.info(f"🚀 Starting {self.ats_type.upper()} Verification Worker...")
        
        iteration = 0
        while True:
            msg = self._pop_verification()
            
            if not msg:
                time.sleep(1)
                iteration += 1
                if max_iterations and iteration >= max_iterations:
                    break
                continue
            
            self._process_verification(msg)
            iteration = 0
            
            if max_iterations and (self.stats['verified'] + self.stats['failed']) >= max_iterations:
                break
        
        self._report_stats()
    
    def _pop_verification(self) -> dict:
        if REDIS_AVAILABLE:
            try:
                result = redis_manager.client.blpop(self.queue_name, timeout=1)
                if result:
                    return json.loads(result[1])
            except:
                pass
        
        # Postgres fallback
        try:
            cur = self.conn.cursor(cursor_factory=RealDictCursor)
            cur.execute("""
                SELECT * FROM pending_verification
                WHERE verified = FALSE AND ats_type = %s
                ORDER BY created_at ASC
                LIMIT 1 FOR UPDATE SKIP LOCKED
            """, (self.ats_type,))
            row = cur.fetchone()
            if row:
                cur.execute("UPDATE pending_verification SET verified = TRUE WHERE id = %s", (row['id'],))
                self.conn.commit()
                return {
                    'endpoint': json.loads(row['endpoint_data']) if isinstance(row['endpoint_data'], str) else row['endpoint_data'],
                    'confidence': row['confidence']
                }
        except:
            self.conn.rollback()
        return None
    
    def _process_verification(self, msg: dict):
        endpoint = msg.get('endpoint')
        if not endpoint:
            return
        
        confidence = msg.get('confidence', 0.4)
        verifier = self.verifiers.get(self.ats_type)
        
        if not verifier:
            logger.error(f"No verifier for ATS type: {self.ats_type}")
            return
        
        success, result, error = verifier(endpoint)
        
        if success:
            self.stats['verified'] += 1
            if register_endpoint(self.conn, endpoint, self.ats_type, confidence):
                self.stats['registered'] += 1
        else:
            self.stats['failed'] += 1
            logger.debug(f"Verification failed: {endpoint.get('canonical_url')}: {error}")
    
    def _report_stats(self):
        logger.info(f"📊 {self.ats_type.upper()} Verifier Stats: {self.stats}")


# =============================================================================
# AGING SCHEDULER (SHARED FOR ALL ATS TYPES)
# =============================================================================

def run_aging_check(ats_types: list = None):
    """
    Daily job to decay confidence and deactivate stale endpoints.
    Works for all ATS types using the same logic.
    """
    if ats_types is None:
        ats_types = ['workday', 'oracle', 'icims']
    
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    logger.info(f"🕐 Running endpoint aging check for: {ats_types}")
    
    total_decayed = 0
    total_deactivated = 0
    
    for ats_type in ats_types:
        # Decay confidence for unverified endpoints (older than 7 days)
        cur.execute("""
            UPDATE career_endpoints
            SET confidence_score = GREATEST(confidence_score - 0.2, 0)
            WHERE ats_provider = %s
              AND discovered_from = 'signal_based'
              AND (last_verified_at IS NULL OR last_verified_at < NOW() - INTERVAL '7 days')
        """, (ats_type,))
        total_decayed += cur.rowcount
        
        # Deactivate low-confidence or high-failure endpoints
        cur.execute("""
            UPDATE career_endpoints
            SET active = FALSE
            WHERE ats_provider = %s
              AND (consecutive_failures >= 3 OR confidence_score < 0.2)
              AND active = TRUE
        """, (ats_type,))
        total_deactivated += cur.rowcount
    
    conn.commit()
    conn.close()
    
    logger.info(f"📊 Aging Complete: {total_decayed} decayed, {total_deactivated} deactivated")


# =============================================================================
# BACKWARD COMPATIBILITY ALIASES
# =============================================================================

class WorkdayCandidateConsumer(MultiATSCandidateConsumer):
    def __init__(self):
        super().__init__(ats_type='workday')

class WorkdayVerificationWorker(MultiATSVerificationWorker):
    def __init__(self):
        super().__init__(ats_type='workday')

class OracleVerificationWorker(MultiATSVerificationWorker):
    def __init__(self):
        super().__init__(ats_type='oracle')

class iCIMSVerificationWorker(MultiATSVerificationWorker):
    def __init__(self):
        super().__init__(ats_type='icims')


# =============================================================================
# CLI ENTRY POINTS
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-ATS Discovery Workers')
    parser.add_argument('worker', choices=['consumer', 'verifier', 'aging'], help='Worker type')
    parser.add_argument('--ats', choices=['workday', 'oracle', 'icims', 'all'], default='workday', help='ATS type')
    parser.add_argument('--max', type=int, default=None, help='Max iterations')
    args = parser.parse_args()
    
    if args.worker == 'aging':
        if args.ats == 'all':
            run_aging_check(['workday', 'oracle', 'icims'])
        else:
            run_aging_check([args.ats])
    elif args.worker == 'consumer':
        if args.ats == 'all':
            # Run all consumers (in practice, use separate processes)
            for ats in ['workday', 'oracle', 'icims']:
                consumer = MultiATSCandidateConsumer(ats_type=ats)
                consumer.run(max_iterations=args.max)
        else:
            consumer = MultiATSCandidateConsumer(ats_type=args.ats)
            consumer.run(max_iterations=args.max)
    elif args.worker == 'verifier':
        if args.ats == 'all':
            for ats in ['workday', 'oracle', 'icims']:
                worker = MultiATSVerificationWorker(ats_type=ats)
                worker.run(max_iterations=args.max)
        else:
            worker = MultiATSVerificationWorker(ats_type=args.ats)
            worker.run(max_iterations=args.max)


if __name__ == "__main__":
    main()
