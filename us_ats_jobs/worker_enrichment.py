import time
import logging
import signal
import sys
import os

# Add root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from us_ats_jobs.db import database
from us_ats_jobs.intelligence.infer import extract_all_enrichment
from us_ats_jobs.intelligence.llm_extractor import LLMService, JobEnrichmentData
from us_ats_jobs.intelligence.extractor_layer1 import extract_skills_fast
from us_ats_jobs.intelligence.extractor_layer2 import extract_skills_semantic, Layer2VectorExtractor

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger("EnrichmentWorker")

# Graceful Shutdown
SHUTDOWN = False
def signal_handler(sig, frame):
    global SHUTDOWN
    logger.info("[SHUTDOWN] Signal received. Finishing current batch...")
    SHUTDOWN = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

from us_ats_jobs.intelligence.skills_db import SkillExtractorDB, extract_skills_with_ids

llm_service = LLMService()
_skill_extractor = None

def get_skill_extractor():
    global _skill_extractor
    if _skill_extractor is None:
        db_config = database.get_db_config()
        _skill_extractor = SkillExtractorDB(db_config)
    return _skill_extractor

def process_batch():
    """
    Fetches a batch of unenriched jobs and processes them with Hybrid Intelligence (Tiered).
    Pipeline:
    1. Layer 1 (FlashText) -> Speed (O(N))
    2. Layer 2 (Vector) -> Recall (Semantic Fallback)
    3. Layer 3 (LLM) -> Reasoning (Premium Only)
    """
    try:
        jobs = database.get_unenriched_jobs(limit=50)
        if not jobs:
            return 0
        
        logger.info(f"[BATCH START] Processing batch of {len(jobs)} jobs...")
        
        count = 0
        for job in jobs:
            if SHUTDOWN: break
            
            job_id = job.get("job_id")
            description = job.get("job_description") or ""
            title = job.get("title") or ""
            company = job.get("company") or "Unknown"
            
            # 0. Set Status to Processing
            database.update_job_status(job_id, 'processing')
            logger.info(f"   --> Marking {job_id} as 'processing'")

            # 0.1 Check for Shared Intelligence (Deduplication)
            desc_hash = job.get('description_hash')
            if desc_hash:
                shared_intel = database.get_enrichment_by_hash(desc_hash)
                if shared_intel:
                    logger.info(f"   --> Found Shared Intelligence for hash {desc_hash[:8]}... Recycling.")
                    # Copy relevant fields (adjusting for RealDictCursor or tuple)
                    # We need to filter out job_id as we want to save it for THIS job_id
                    final_data = dict(shared_intel)
                    final_data.pop('job_id', None)
                    final_data.pop('enriched_at', None)
                    
                    final_data['enrichment_source'] = f"recycled:{shared_intel.get('job_id', 'unknown')}"
                    
                    database.save_enrichment(job_id, final_data)
                    database.update_job_status(job_id, 'completed')
                    count += 1
                    continue

            final_data = {}
            current_tier = 'basic'
            current_source = 'flashtext'

            try:
                # --- LAYER 1: FlashText (Speed - O(N)) ---
                ft_skills = set(extract_skills_fast(description))
                
                # --- LAYER: Skill Ontology (Normalized IDs) ---
                # This uses the SkillExtractorDB to map to MIND Ontology IDs
                ontology_names, ontology_ids = [], []
                try:
                    extractor = get_skill_extractor()
                    ontology_names, ontology_ids = extract_skills_with_ids(description, database.get_db_config())
                    logger.info(f"   --> Ontology matched {len(ontology_ids)} skills for {job_id}")
                except Exception as ont_err:
                    logger.warning(f"Ontology extraction failed for {job_id}: {ont_err}")
                
                final_data = {
                    "tech_languages": ", ".join(list(ft_skills.union(set(ontology_names)))),
                    "extracted_skill_count": len(ft_skills.union(set(ontology_names))),
                    "skill_ids": ontology_ids
                }
                
                # --- LAYER 2: Vector Search (Recall - Semantic) ---
                # Strategy: Run if FlashText/Ontology found few results
                semantic_skills = set()
                if len(ft_skills) < 8:
                    semantic_skills = set(extract_skills_semantic(description))
                    if semantic_skills:
                        current_source = 'hybrid-vector'
                        logger.info(f"   --> Layer 2 found {len(semantic_skills)} extra skills for {job_id}")

                # Combine all sources for tech_languages
                all_skills = ft_skills.union(semantic_skills).union(set(ontology_names))

                # Run Legacy Regex for other fields (Exp, Edu)
                legacy_data = extract_all_enrichment(description, title=title)
                # Ensure we don't overwrite the skill_ids and tech_languages we just carefully built
                final_data.update({k: v for k, v in legacy_data.items() if k not in ["tech_languages", "skill_ids"]})
                
                # Merge Skills: Legacy Regex + FlashText + Semantic + Ontology
                legacy_tech = set((legacy_data.get("tech_languages") or "").split(", "))
                all_skills.update(legacy_tech)
                all_skills.discard("")
                
                # Save merged skills and IDs
                final_data["tech_languages"] = ", ".join(list(all_skills)) 
                final_data["skill_ids"] = ontology_ids # Keep the normalized IDs

                # --- LAYER 3: LLM (Reasoning - Expensive) ---
                # Run if High Value (Senior/Lead) OR if Low Skill Count (Rescue Mode)
                should_run_llm = (
                    len(all_skills) > 10 or 
                    "senior" in title.lower() or 
                    "lead" in title.lower() or 
                    len(all_skills) < 3  # Rescue mode: try to find something if other layers failed
                )

                if should_run_llm:
                    if llm_service and llm_service.client:
                        try:
                            llm_result = llm_service.extract(description, title, company)
                            if llm_result:
                                final_data["visa_sponsorship"] = "Yes" if llm_result.visa_sponsorship.mentioned else "No"
                                if llm_result.salary.extracted:
                                    final_data["salary_min"] = llm_result.salary.min
                                    final_data["salary_max"] = llm_result.salary.max
                                
                                final_data["seniority_tier"] = llm_result.seniority
                                final_data["job_summary"] = llm_result.summary
                                
                                # Add LLM extracted skills to the pool
                                if llm_result.tech_stack:
                                    # Assuming llm_result.tech_stack is a list or string, verify structure if needed
                                    # But for now, just note that we aren't explicitly merging LLM skills back into 'tech_languages' here 
                                    # unless we want to. Let's assume LLM augments the 'final_data' directly if designed so, 
                                    # but based on previous code it was mostly enriching metadata. 
                                    # Let's keep it safe.
                                    pass

                                current_tier = 'premium'
                                current_source = 'llm-hybrid'
                        except Exception as llm_err:
                            logger.warning(f"LLM skipped for {job_id}: {llm_err}")

                # 4. Generate Embedding (Layer 2)
                # Used for Hybrid Semantic Search
                try:
                    extractor = Layer2VectorExtractor()
                    # Use Title + Description for better context
                    text_to_embed = f"{title}. {description}"
                    embedding = extractor.embed_text(text_to_embed)
                    if embedding:
                        final_data["embedding"] = embedding
                        logger.info(f"   --> Generated embedding (dim: {len(embedding)})")
                except Exception as emb_err:
                    logger.warning(f"Embedding extraction failed: {emb_err}")

                # 5. Save to DB
                final_data["enrichment_tier"] = current_tier
                final_data["enrichment_source"] = current_source

                database.save_enrichment(job_id, final_data)
                database.update_job_status(job_id, 'completed')
                count += 1
                
            except Exception as e:
                logger.error(f"[ERROR] Enriching job {job_id}: {e}")
                database.fail_job(job_id)
        
        logger.info(f"[BATCH DONE] Enriched {count} jobs (Tiered Mode).")
        return count

    except Exception as e:
        logger.error(f"[ERROR] Batch error: {e}")
        time.sleep(5)
        return 0

def worker_loop():
    logger.info("[START] Enrichment Worker started. Waiting for jobs...")
    
    # Init DB Pool
    if hasattr(database, "init_pool"):
        database.init_pool()
        
    while not SHUTDOWN:
        processed = process_batch()
        
        if processed == 0:
            # If no jobs, sleep for a bit
            time.sleep(5)
        else:
            # If we had jobs, fast loop to drain queue? 
            # Or small sleep to be nice to DB
            time.sleep(0.1)

    logger.info("[STOP] Enrichment Worker stopped.")

if __name__ == "__main__":
    worker_loop()
