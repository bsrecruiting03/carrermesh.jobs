import sys
import os
import logging
import psycopg2

# Add api dir to path so we can import database and config
# We are in scripts/, parent is root, we want root/api
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
api_dir = os.path.join(root_dir, 'api')
sys.path.append(api_dir)

from database import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    migration_file = os.path.join(os.path.dirname(__file__), 'migration_05_fix_trigger.sql')
    
    logger.info(f"Reading migration file: {migration_file}")
    with open(migration_file, 'r') as f:
        sql = f.read()
        
    logger.info("Connecting to database...")
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                logger.info("Executing migration...")
                cur.execute(sql)
                conn.commit()
                logger.info("Migration successful! job_search table updated.")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
