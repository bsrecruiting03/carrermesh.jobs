import sys
import os
import logging

# Add root project directory to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from us_ats_jobs.db import database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test():
    job_id = "https://jobs.boeing.com/job/bengaluru/experienced-programmer-analyst-salesforce/185/89859738080"
    logger.info(f"Testing projection for: {job_id}")
    try:
        database.upsert_job_search_projection([job_id])
        logger.info("Success for single job!")
    except Exception as e:
        logger.error(f"Failed for single job: {e}")

    # Check batch of 2 with same job twice
    try:
        database.upsert_job_search_projection([job_id, job_id])
        logger.info("Success for duplicate batch!")
    except Exception as e:
        logger.error(f"Failed for duplicate batch: {e}")

if __name__ == "__main__":
    test()
