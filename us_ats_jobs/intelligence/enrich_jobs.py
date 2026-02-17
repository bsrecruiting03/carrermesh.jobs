"""
Batch Job Enrichment Pipeline (v4 - MIND Ontology Integrated + Multi-Layer)
Enriches jobs with comprehensive intelligence:
- Layer 1: FlashText + MIND Ontology (Speed)
- Layer 2: Vector Search (Recall - for hard-to-parse jobs)
- Layer 3: LLM Extraction (Reasoning - for high-value or empty-skill jobs)
"""

import sys
import os
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from typing import List, Dict, Optional, Any
import re
import time

# Add the root directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from us_ats_jobs.intelligence.skills import SkillExtractor
from us_ats_jobs.intelligence.skills_db import SkillExtractorDB, extract_skills_with_ids
from us_ats_jobs.intelligence.qualifications import QualificationsExtractor
from us_ats_jobs.intelligence.salary_extractor import extract_salary

# Import Advanced Layers
try:
    from us_ats_jobs.intelligence.extractor_layer2 import extract_skills_semantic, Layer2VectorExtractor
    from us_ats_jobs.intelligence.llm_extractor import LLMService
except ImportError:
    print("Warning: Could not import Layer 2/3 extractors. Ensure dependencies are installed.")
    extract_skills_semantic = None
    Layer2VectorExtractor = None
    LLMService = None

# Configuration
DB_URL = "postgresql://postgres:password@localhost:5433/job_board"
BATCH_SIZE = 100

# Database config for SkillExtractorDB
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "job_board",
    "user": "postgres",
    "password": "password"
}

def get_db_connection():
    return psycopg2.connect(DB_URL)

def extract_experience(text: str) -> Optional[int]:
    """Simple regex-based experience extraction."""
    if not text:
        return None
    match = re.search(r'(\d+)\s*(?:\+)?\s*(?:year|yr)', text, re.IGNORECASE)
    if match:
        try:
            val = int(match.group(1))
            return val if val < 50 else None
        except:
            return None
    return None

def enrich_jobs(limit: Optional[int] = None, verbose: bool = False, force: bool = False):
    """Fetches jobs and updates enrichment table with comprehensive intelligence."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Initialize Extractors
    skill_extractor = SkillExtractor()  # Layer 1: Regex/FlashText
    skill_extractor_db = SkillExtractorDB(DB_CONFIG)  # Layer 1B: MIND Ontology
    qual_extractor = QualificationsExtractor()
    
    # Initialize Layer 3 (LLM)
    llm_service = None
    if LLMService:
        try:
            llm_service = LLMService()
            print("LLM Service initialized.")
        except Exception as e:
            print(f"Failed to init LLM Service: {e}")

    # Initialize Layer 2 (Vector) - instantiated on demand or here?
    # Simple semantic extraction function is stateless usually, but embedding might need init.
    
    # Fetch jobs
    # IF force=True, we ignore the enrichment_status check
    where_clause = ""
    if not force:
        where_clause = """
            WHERE (
                j.enrichment_status = 'pending' OR 
                j.enrichment_status IS NULL OR
                j.enrichment_status = 'stale'
            )
        """
    else:
        where_clause = "WHERE 1=1" # Process everything subject to limit

    query = f"""
        SELECT j.job_id, j.title, j.job_description, j.company 
        FROM jobs j
        {where_clause}
        AND j.job_description IS NOT NULL
        AND LENGTH(j.job_description) > 50
        ORDER BY j.job_id DESC
        LIMIT %s
    """
    
    fetch_limit = limit if limit else 100000
    cur.execute(query, (fetch_limit,))
    
    jobs = cur.fetchall()
    total_found = len(jobs)
    print(f"Found {total_found} jobs to enrich (Force={force}).")
    
    if total_found == 0:
        skill_extractor_db.close()
        conn.close()
        return
    
    processed_count = 0
    stats = {
        "skills_l1": 0,
        "skills_l2": 0,
        "skills_l3": 0,
        "seniority": 0,
        "certs": 0
    }
    
    job_skills_data = []
    
    for i in range(0, total_found, BATCH_SIZE):
        batch = jobs[i:i + BATCH_SIZE]
        enrichment_data = []
        
        for row in batch:
            # Unpack safely (handle if company column is missing in query or tuple)
            if len(row) == 4:
                job_id, title, description, company = row
            else:
                job_id, title, description = row[:3]
                company = "Unknown"

            full_text = f"{title}\n\n{description}" if title and description else (title or description or "")
            
            # --- LAYER 1: FlashText / Regex ---
            extracted_skills = skill_extractor.extract(description) # List[ExtractedSkill]
            l1_skill_names = set(s.canonical_name for s in extracted_skills)
            
            # --- LAYER 1B: MIND Ontology ---
            skills_from_db = skill_extractor_db.extract(full_text)
            
            # Merge L1 and L1B
            all_skill_names = l1_skill_names.union(s.canonical_name for s in skills_from_db)
            
            # --- LAYER 2: Semantic / Vector (If needed) ---
            # Run if few skills found (< 8)
            l2_found_count = 0
            if extract_skills_semantic and len(all_skill_names) < 8:
                try:
                    semantic_skills = extract_skills_semantic(description)
                    if semantic_skills:
                        l2_found_count = len(semantic_skills)
                        all_skill_names.update(semantic_skills)
                        if verbose: print(f"  [L2] Found {l2_found_count} semantic skills for {job_id}")
                except Exception as e:
                    if verbose: print(f"  [L2] Error: {e}")

            # --- LAYER 3: LLM (If needed) ---
            # Run if very few skills (< 3) OR Senior Role
            l3_info = {}
            run_llm = False
            if llm_service:
                is_senior = "senior" in (title or "").lower() or "lead" in (title or "").lower()
                is_rescue = len(all_skill_names) < 3
                if is_senior or is_rescue:
                    run_llm = True

            if run_llm and llm_service:
                try:
                    llm_res = llm_service.extract(description, title, company)
                    if llm_res:
                        l3_info['seniority'] = llm_res.seniority
                        l3_info['summary'] = llm_res.summary
                        if llm_res.salary.extracted:
                            l3_info['salary_min'] = llm_res.salary.min
                            l3_info['salary_max'] = llm_res.salary.max
                        # If LLM found skills? (The Service currently returns 'tech_stack' sometimes)
                        # We won't merge them here to keep 'all_skill_names' clean for now, 
                        # relying on L1/L2 for the main tags, but we could.
                except Exception as e:
                     if verbose: print(f"  [L3] Error: {e}")

            # --- Finalize Skills ---
            # We need to create a finalized list of Skill IDs for the `skill_ids` column
            # For skills found via L1/L2 that match MIND ontology, we get IDs.
            # Currently `skills_from_db` has the L1B IDs.
            # L1/L2 are just names. We can try to map them back to IDs if we had a reverse lookup.
            # For now, we will rely on `skills_from_db` (L1B) to populate `skill_ids` 
            # and `all_skill_names` to populate the text columns.
            
            skill_ids = [skill.skill_id for skill in skills_from_db]
            
            # Populate job_skills table (only for L1B currently as they have IDs)
            for skill in skills_from_db:
                job_skills_data.append((
                    job_id,
                    skill.skill_id,
                    'enrichment_batch',
                    skill.confidence,
                    skill.matched_synonym
                ))
            
            # --- Qualifications ---
            qual_result = qual_extractor.extract_all(title, description)
            exp_years = extract_experience(description)
            
            # Overwrite seniority with LLM if available
            seniority_tier = l3_info.get('seniority') or qual_result.seniority_tier

            # Stats
            if len(l1_skill_names) > 0: stats["skills_l1"] += 1
            if l2_found_count > 0: stats["skills_l2"] += 1
            if run_llm: stats["skills_l3"] += 1
            if seniority_tier != "Unknown": stats["seniority"] += 1

            # Prepare Data Row
            # CATEGORIZATION LOGIC
            final_languages = []
            final_frameworks = []
            final_tools = []
            final_specs = []
            
            for s in skills_from_db:
                name = s.canonical_name
                cats = [c.lower() for c in s.category]
                domains = [d.lower() for d in s.technical_domains]
                
                if any(c in cats for c in ['programminglanguage', 'scriptinglanguage']):
                    final_languages.append(name)
                elif 'framework' in cats:
                    final_frameworks.append(name)
                elif any(c in cats for c in ['industryintent', 'domainexpertise', 'architecturepattern', 'cloudservice']):
                    final_specs.append(name)
                elif any(d in domains for d in ['fintech', 'healthcare', 'cybersecurity', 'blockchain', 'ai', 'machine learning']):
                    final_specs.append(name)
                else:
                    final_tools.append(name)

            # Salary Extraction (Layer 1 Regex)
            smin, smax, scurr = extract_salary(description)

            enrichment_data.append((
                job_id,
                l3_info.get('summary'),  # summary
                ", ".join(list(set(final_languages))),
                ", ".join(list(set(final_frameworks))),
                "", # tech_cloud
                ", ".join(list(set(final_tools))),
                ", ".join(list(set(final_specs))),
                exp_years,
                seniority_tier,
                qual_result.seniority_level,
                qual_result.education_level,
                ", ".join(qual_result.certifications),
                ", ".join(qual_result.soft_skills),
                skill_ids,
                len(all_skill_names),
                datetime.now(),
                smin or l3_info.get('salary_min'),
                smax or l3_info.get('salary_max'),
                scurr or 'USD'
            ))

        # Bulk upsert
        upsert_query = """
            INSERT INTO job_enrichment (
                job_id, job_summary, 
                tech_languages, tech_frameworks, tech_cloud, tech_tools, specializations,
                experience_years, 
                seniority_tier, seniority_level, education_level, certifications, soft_skills,
                skill_ids, extracted_skill_count,
                last_enriched_at
            ) VALUES %s
            ON CONFLICT (job_id) DO UPDATE SET
                tech_languages = EXCLUDED.tech_languages,
                tech_frameworks = EXCLUDED.tech_frameworks,
                tech_tools = EXCLUDED.tech_tools,
                specializations = EXCLUDED.specializations,
                skill_ids = EXCLUDED.skill_ids,
                extracted_skill_count = EXCLUDED.extracted_skill_count,
                last_enriched_at = EXCLUDED.last_enriched_at,
                job_summary = COALESCE(EXCLUDED.job_summary, job_enrichment.job_summary),
                seniority_tier = COALESCE(EXCLUDED.seniority_tier, job_enrichment.seniority_tier)
        """
        
        upsert_jobs_query = """
            UPDATE jobs SET
                salary_min = v.smin,
                salary_max = v.smax,
                salary_currency = v.scurr,
                enrichment_status = 'completed'
            FROM (VALUES %s) AS v (job_id, smin, smax, scurr)
            WHERE jobs.job_id = v.job_id
        """
        
        try:
            execute_values(cur, upsert_query, enrichment_data)
            
            # Update jobs table status and salary
            jobs_salary_data = [(row[0], row[16], row[17], row[18]) for row in enrichment_data]
            execute_values(cur, upsert_jobs_query, jobs_salary_data)

            if job_skills_data:
                # ... [existing job_skills logic]
                job_skills_query = """
                    INSERT INTO job_skills (job_id, skill_id, extraction_source, extraction_confidence, matched_synonym)
                    VALUES %s
                    ON CONFLICT (job_id, skill_id) DO UPDATE SET
                        extraction_confidence = EXCLUDED.extraction_confidence
                """
                execute_values(cur, job_skills_query, job_skills_data)
                job_skills_data = []

            conn.commit()
            processed_count += len(batch)
            if verbose: print(f"Processed batch {processed_count} jobs...")
            
        except Exception as e:
            print(f"Error executing batch: {e}")
            conn.rollback()
            # Mark batch as failed
            try:
                job_ids = [row[0] for row in batch]
                cur.execute("UPDATE jobs SET enrichment_status = 'failed' WHERE job_id = ANY(%s)", (job_ids,))
                conn.commit()
            except:
                pass

    skill_extractor_db.close()
    cur.close()
    conn.close()
    
    print(f"\nENRICHMENT COMPLETE. Total: {processed_count}")
    print(f"Stats: L1(Regex): {stats['skills_l1']}, L2(Vector): {stats['skills_l2']}, L3(LLM): {stats['skills_l3']}")

if __name__ == "__main__":
    limit = 1000
    verbose = False
    force = False
    
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    if len(sys.argv) > 2:
        verbose = sys.argv[2].lower() == 'true'
    if len(sys.argv) > 3:
        force = sys.argv[3].lower() == 'true'
    
    print(f"Starting enrichment... (Limit={limit}, Verbose={verbose}, Force={force})")
    enrich_jobs(limit=limit, verbose=verbose, force=force)

