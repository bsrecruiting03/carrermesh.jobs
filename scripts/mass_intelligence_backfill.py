import sys
import os
import logging
from tqdm import tqdm
from datetime import datetime

# Add root project directory to path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(root_dir)

from us_ats_jobs.db import database
from us_ats_jobs.intelligence.skills_db import SkillExtractorDB
from us_ats_jobs.intelligence.salary_extractor import extract_salary
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MassIntelligenceBackfill")

def run_mass_backfill(limit=None, batch_size=2000, force=False):
    """
    Massive backfill for all jobs:
    - Re-extract skills using 5k+ ontology
    - Re-extract salary using new robust regex
    - Update both 'jobs' and 'job_enrichment' tables
    """
    db_config = database.get_db_config()
    extractor = SkillExtractorDB(db_config)
    
    with database.get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Identify jobs to process
            # We look for jobs that haven't been synced with the latest ontology
            # or force all if requested.
            where_clause = "WHERE je.ontology_synced_at IS NULL"
            if force:
                where_clause = "WHERE 1=1"
            
            count_query = f"SELECT count(*) FROM job_enrichment je {where_clause}"
            cur.execute(count_query)
            total = cur.fetchone()[0]
            if limit: total = min(total, limit)
            
            logger.info(f"🚀 Starting Mass Backfill for {total} jobs...")
            
            processed = 0
            pbar = tqdm(total=total, desc="Backfilling Intelligence")
            
            while processed < total:
                # Fetch batch
                fetch_size = min(batch_size, total - processed)
                cur.execute(f"""
                    SELECT j.job_id, j.job_description, j.title, j.salary_min, j.salary_max
                    FROM jobs j
                    JOIN job_enrichment je ON j.job_id = je.job_id
                    {where_clause}
                    LIMIT %s
                """, (fetch_size,))
                
                rows = cur.fetchall()
                if not rows: break
                
                enrichment_updates = []
                job_updates = []
                
                for job_id, description, title, curr_smin, curr_smax in rows:
                    if not description: continue

                    # A. Skill Extraction (L1 Fast with Implication)
                    combined_text = f"{title}\n\n{description}" if title else description
                    skills_objs = extractor.extract(combined_text, expand_implications=True)
                    
                    skill_ids = [s.skill_id for s in skills_objs]
                    
                    # CATEGORIZATION LOGIC
                    langs = []
                    fworks = []
                    tools = []
                    specs = []
                    
                    for s in skills_objs:
                        name = s.canonical_name
                        cats = [c.lower() for c in s.category]
                        domains = [d.lower() for d in s.technical_domains]
                        
                        if any(c in cats for c in ['programminglanguage', 'scriptinglanguage']):
                            langs.append(name)
                        elif 'framework' in cats:
                            fworks.append(name)
                        elif any(c in cats for c in ['industryintent', 'domainexpertise', 'architecturepattern', 'cloudservice']):
                            specs.append(name)
                        elif any(d in domains for d in ['fintech', 'healthcare', 'cybersecurity', 'blockchain', 'ai', 'machine learning']):
                            specs.append(name)
                        else:
                            tools.append(name)
                    
                    # B. Salary Extraction (Robust Regex)
                    smin, smax, scurr = extract_salary(description)
                    
                    # C. Queue Enrichment Update
                    enrichment_updates.append((
                        skill_ids, 
                        ", ".join(list(set(langs))), 
                        ", ".join(list(set(fworks))),
                        ", ".join(list(set(tools))),
                        ", ".join(list(set(specs))),
                        len(skill_ids), 
                        job_id
                    ))
                    
                    # D. Queue Job Table Update (Salary)
                    if smin is not None:
                        job_updates.append((smin, smax, scurr, job_id))
                
                # Execute Updates
                if enrichment_updates:
                    # Update job_enrichment
                    execute_values(cur, """
                        UPDATE job_enrichment AS je SET
                            skill_ids = v.skill_ids::int[],
                            tech_languages = v.tech_languages,
                            tech_frameworks = v.tech_frameworks,
                            tech_tools = v.tech_tools,
                            specializations = v.specs,
                            extracted_skill_count = v.extracted_skill_count,
                            ontology_synced_at = NOW()
                        FROM (VALUES %s) AS v (skill_ids, tech_languages, tech_frameworks, tech_tools, specs, extracted_skill_count, job_id)
                        WHERE je.job_id = v.job_id
                    """, enrichment_updates)
                
                if job_updates:
                    # Update jobs (Salary columns)
                    execute_values(cur, """
                        UPDATE jobs AS j SET
                            salary_min = v.smin,
                            salary_max = v.smax,
                            salary_currency = v.scurr,
                            enrichment_status = 'completed'
                        FROM (VALUES %s) AS v (smin, smax, scurr, job_id)
                        WHERE j.job_id = v.job_id
                    """, job_updates)
                
                conn.commit()
                processed += len(rows)
                pbar.update(len(rows))

            pbar.close()

    logger.info("✅ Global Mass Backfill Complete!")

if __name__ == "__main__":
    # Default to 10k test, then run full
    limit = None
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    
    force = False
    if len(sys.argv) > 2:
        force = sys.argv[2].lower() == 'true'
        
    run_mass_backfill(limit=limit, force=force)
