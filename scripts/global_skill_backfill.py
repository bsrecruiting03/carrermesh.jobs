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
logger = logging.getLogger("GlobalSkillBackfill")

def run_backfill(batch_size=1000):
    """
    Scans descriptions of all jobs with missing skills and updates them.
    """
    db_config = database.get_db_config()
    extractor = SkillExtractorDB(db_config)
    
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Count total to process
            cur.execute("""
                SELECT count(*) 
                FROM job_enrichment je
                WHERE je.ontology_synced_at IS NULL
            """)
            total = cur.fetchone()[0]
            logger.info(f"Total jobs to backfill: {total}")

            # 2. Iterate in batches
            processed = 0
            while processed < total:
                cur.execute("""
                    SELECT je.job_id, j.job_description, j.title
                    FROM job_enrichment je
                    JOIN jobs j ON je.job_id = j.job_id
                    WHERE je.ontology_synced_at IS NULL
                    LIMIT %s
                """, (batch_size,))
                rows = cur.fetchall()
                if not rows:
                    break
                
                update_data = []
                for job_id, description, title in rows:
                    if not description:
                        update_data.append(([], "", 0, job_id))
                        continue

                    # Extract skills using the ontology (combined text)
                    combined_text = f"{title}\n\n{description}" if title else description
                    skills_objs = extractor.extract(combined_text)

                    skill_names = [s.canonical_name for s in skills_objs]
                    skill_ids = [s.skill_id for s in skills_objs]
                    
                    update_data.append((skill_ids, ", ".join(skill_names), len(skill_ids), job_id))
                
                if update_data:
                    from psycopg2.extras import execute_values
                    execute_values(cur, """
                        UPDATE job_enrichment AS je SET
                            skill_ids = v.skill_ids::int[],
                            tech_languages = v.tech_languages,
                            extracted_skill_count = v.extracted_skill_count,
                            ontology_synced_at = NOW()
                        FROM (VALUES %s) AS v (skill_ids, tech_languages, extracted_skill_count, job_id)
                        WHERE je.job_id = v.job_id
                    """, update_data)
                
                conn.commit()
                processed += len(rows)
                logger.info(f"Progress: {processed}/{total}...")

    logger.info("Global backfill complete!")

if __name__ == "__main__":
    run_backfill()
