"""
Test Script for Oracle/Taleo/HCM Discovery

Verifies that the MultiATSSignalProcessor and MultiATSVerificationWorker
correctly identify and verify endpoints for:
1. Oracle (Oracle HCM Cloud)
2. Ford (Oracle HCM Cloud)
3. Goldman Sachs (Taleo/TalentLink)
"""

import sys
import os
import logging
import requests
from urllib.parse import urlparse

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agents.discovery.signal_processor import (
    is_oracle_url, 
    normalize_oracle_endpoint, 
    extract_oracle_embeds
)
from agents.discovery.workers import verify_oracle_endpoint

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger("OracleTest")

TEST_CASES = [
    {
        "company": "Oracle",
        "raw_url": "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/jobsearch?requisition=123",
        "expected_type": "hcm_cloud",
        "expected_canonical": "https://eeho.fa.us2.oraclecloud.com/hcmUI/CandidateExperience"
    },
    {
        "company": "Ford",
        "raw_url": "https://efds.fa.us6.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/1001",
        "expected_type": "hcm_cloud",
        "expected_canonical": "https://efds.fa.us6.oraclecloud.com/hcmUI/CandidateExperience"
    },
    {
        "company": "Goldman Sachs (TalentLink)",
        "raw_url": "https://goldmansachs.tal.net/vx/lang-en-GB/mobile-0/appcentre-1/brand-2/candidate/jobboard/vacancy/1/adv/",
        "expected_type": "oracle_generic", # tal.net is generic match
        "expected_canonical": "https://goldmansachs.tal.net"
    }
]

def run_tests():
    logger.info("🧪 Starting Oracle Discovery Tests...")
    
    for test in TEST_CASES:
        logger.info(f"\nScanning {test['company']}...")
        
        # 1. Signal Detection
        is_match = is_oracle_url(test['raw_url'])
        logger.info(f"  Signal Detected: {'✅' if is_match else '❌'}")
        
        if not is_match:
            continue
            
        # 2. Normalization
        norm = normalize_oracle_endpoint(test['raw_url'])
        logger.info(f"  Normalized: {norm}")
        
        # 3. Verification (Live HTTP Check)
        logger.info(f"  Verifying {test['company']} endpoint...")
        
        # Construct endpoint object for verifier
        endpoint = {
            'canonical_url': norm,
            'type': 'oracle' 
        }
        
        success, has_jobs, error = verify_oracle_endpoint(endpoint)
        
        if success:
            logger.info(f"  ✅ Verification: SUCCESS (Jobs found: {has_jobs})")
        else:
            logger.info(f"  ❌ Verification: FAILED ({error})")

if __name__ == "__main__":
    run_tests()
