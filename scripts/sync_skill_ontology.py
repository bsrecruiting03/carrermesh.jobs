import sys
import os
import logging
from tqdm import tqdm

# Add root project directory to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from us_ats_jobs.db import database
from us_ats_jobs.intelligence.skills_db import SkillExtractorDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SyncSkillOntology")

def sync_existing():
    """
    Maps existing tech_languages strings to skill_ids using the ontology.
    """
    db_config = database.get_db_config()
    extractor = SkillExtractorDB(db_config)
    
    # 1. Get jobs with text skills but no IDs
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT job_id, tech_languages 
                FROM job_enrichment 
                WHERE tech_languages <> '' 
                AND tech_languages IS NOT NULL 
                AND (skill_ids IS NULL OR cardinality(skill_ids) = 0)
            """)
            rows = cur.fetchall()
            logger.info(f"Found {len(rows)} jobs to sync.")

            for job_id, tech_text in tqdm(rows, desc="Syncing Skills"):
                # Use ontology canonical names and synonyms to find IDs
                # We can either re-extract from description (better) or map from tech_text
                # Since we want consistency, we'll try to map from tech_text first 
                # but if that fails, we can't do much without description.
                # Actually, many tech_languages are comma separated.
                
                skill_names = [s.strip() for s in tech_text.split(",") if s.strip()]
                skill_ids = []
                for name in skill_names:
                    skill_data = extractor.get_skill_by_name(name)
                    if skill_data:
                        skill_ids.append(skill_data['skill_id'])
                
                if skill_ids:
                    skill_ids = list(set(skill_ids))
                    cur.execute("""
                        UPDATE job_enrichment 
                        SET skill_ids = %s 
                        WHERE job_id = %s
                    """, (skill_ids, job_id))
        
        conn.commit()
    
    logger.info("Sync complete!")

if __name__ == "__main__":
    sync_existing()
