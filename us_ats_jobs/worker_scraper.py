import sys
import os
import time
import logging
import signal
from pythonjsonlogger import jsonlogger

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from us_ats_jobs.db import database
from us_ats_jobs.queue.redis_manager import queue_manager
from us_ats_jobs.utils.crawler_utils import robots_manager

# Import Monitoring
from api.monitoring import Monitor

# Import Fetchers & Normalizers
from us_ats_jobs.sources.greenhouse import fetch_greenhouse_jobs
from us_ats_jobs.sources.lever import fetch_lever_jobs
from us_ats_jobs.sources.ashby import fetch_ashby_jobs
from us_ats_jobs.sources.workable import fetch_workable_jobs
from us_ats_jobs.sources.workday import fetch_workday_jobs
from us_ats_jobs.sources.workday import fetch_workday_jobs
from us_ats_jobs.sources.bamboohr import fetch_bamboohr_jobs
from us_ats_jobs.sources.generic import fetch_generic_jobs
from us_ats_jobs.sources.universal import fetch_universal_jobs

from us_ats_jobs.normalizer import (
    normalize_greenhouse,
    normalize_lever,
    normalize_ashby,
    normalize_workable,
    normalize_workday,
    normalize_bamboohr
)

# Configure Structured Logging
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter(
    '%(asctime)s %(levelname)s %(name)s %(message)s %(correlation_id)s %(company_name)s'
)
logHandler.setFormatter(formatter)
logger = logging.getLogger("Worker")
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
logger.propagate = False # Avoid double logging if root has a handler

# Graceful Shutdown
SHUTDOWN = False
def signal_handler(sig, frame):
    global SHUTDOWN
    logger.info("🛑 Shutdown signal received. Finishing current task...")
    SHUTDOWN = True
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def process_company(task):
    """
    Executes scraping logic for a single task (Company or Endpoint).
    """
    start_time = time.time()
    
    # Handle inputs
    task_type = task.get("type", "company_crawl") # Default to old type
    
    if task_type == "endpoint_ingest":
        # New Endpoint-Driven Flow
        endpoint_id = task.get("endpoint_id")
        provider = task.get("ats_provider")
        # Use slug as company name proxy if not provided
        name = task.get("ats_slug") or "Unknown"
        endpoint_url = task.get("endpoint_url")
        retry_count = task.get("retry_count", 0)
        correlation_id = task.get("correlation_id", "N/A")
        company_id = None # Decoupled!
        
        # Log Context
        log_context = {"correlation_id": correlation_id, "endpoint_id": endpoint_id, "provider": provider}
        logger.info(f"🔄 Ingesting Endpoint: {endpoint_url} ({provider})", extra=log_context)
        
    else:
        # Legacy Company-Driven Flow
        name = task.get("name")
        company_id = task.get("id")
        provider = task.get("ats_provider")
        correlation_id = task.get("correlation_id", "N/A")
        retry_count = task.get("retry_count", 0)
        endpoint_url = task.get("ats_url") # Map legacy field
        
        log_context = {"correlation_id": correlation_id, "company_name": name}
        logger.info(f"🔄 Processing Company: {name} ({provider})", extra=log_context)
    
    # 1. Robots Check (Skip for now or implement per-domain check)
    # robots_manager.can_fetch(endpoint_url)...

    try:
        raw_jobs = []
        normalized_jobs = []
        
        # 2. Fetch & Normalize
        # Most fetchers take 'company' (slug/name). 
        # For endpoint ingestion, 'name' IS the slug usually.
        
        if provider == "greenhouse":
            # Greenhouse fetcher expects board token (slug)
            raw_jobs = fetch_greenhouse_jobs(name, endpoint_url)
            normalized_jobs = [normalize_greenhouse(j, name) for j in raw_jobs]
            
        elif provider == "lever":
            raw_jobs = fetch_lever_jobs(name, endpoint_url)
            normalized_jobs = [normalize_lever(j, name) for j in raw_jobs]
            
        elif provider == "ashby":
            raw_jobs = fetch_ashby_jobs(name, endpoint_url)
            normalized_jobs = [normalize_ashby(j, name) for j in raw_jobs]
            
        elif provider == "workable":
            # Workable needs slug
            raw_jobs = fetch_workable_jobs(name)
            normalized_jobs = [normalize_workable(j, name) for j in raw_jobs]
            
        elif provider == "bamboohr":
            # BambooHR needs subdomain (slug)
            raw_jobs = fetch_bamboohr_jobs(name)
            normalized_jobs = [normalize_bamboohr(j, name) for j in raw_jobs]
        
        elif provider == "workday":
             raw_jobs = fetch_workday_jobs(name) or []
             normalized_jobs = [normalize_workday(j, name, name) for j in raw_jobs]
             
        elif provider.startswith("custom_"):
            # Custom Adapter Flow
            # 1. Load Adapter
            from importlib import import_module
            try:
                # e.g. custom_amazon -> amazon
                adapter_name = provider.replace("custom_", "")
                module_name = f"us_ats_jobs.adapters.{adapter_name}"
                
                # Import module
                mod = import_module(module_name)
                
                # Find class (Assuming ClassName is TitleCase of adapter_name, e.g. AmazonAdapter)
                # Or we enforce a standard name "Adapter" in the module?
                # Let's search for subclass of PublisherAdapter or use standard convention.
                # Convention: AmazonAdapter
                class_name = f"{adapter_name.capitalize()}Adapter"
                adapter_class = getattr(mod, class_name)
                
                adapter = adapter_class()
                
                # 2. Fetch Loop
                cursor = None
                total_fetched = 0
                
                logger.info(f"🔌 Starting Custom Adapter: {class_name}", extra=log_context)
                
                while True:
                    batch_raw = adapter.fetch_jobs(cursor)
                    if not batch_raw:
                        break
                        
                    # Normalize (Pass-through for raw jobs basically, or basic mapping)
                    # The prompt said: "Reuses the existing normalization pipeline"
                    # But Custom Adapters return RAW payloads.
                    # We need a normalizer for each custom adapter OR generic one?
                    # "Adapters MUST: Return raw job payloads... NOT normalize jobs"
                    # But insert_jobs expects normalized structure?
                    # "Pass raw jobs to raw_jobs.insert()... EXISTING normalization pipeline"
                    # Ideally we normalize HERE.
                    # Let's check `database.py`. `insert_jobs(jobs)` expects dicts that have `title`, `description`, etc.
                    # So Custom Adapters returns list of dicts. Are these dicts ALREADY normalized keys?
                    # The prompt said "Return raw job payloads". 
                    # If I pass raw Amazon payload to `insert_jobs`, it will look for `title`, `job_description`.
                    # Amazon has `title`, `description_short` (maybe description?).
                    # I need to normalize these specific to the adapter.
                    # I will add a `normalize` method to the Adapter Interface? 
                    # Or implement `normalize_amazon` in normalizer.py?
                    # Let's do `normalize_amazon` in normalizer for consistency.
                    
                    # For now, I will assume I need to normalize them.
                    # I will import dynamic normalizer? 
                    # Or just map known fields if the adapter converts them?
                    # Let's stick to the prompt: "Reuses the existing normalization pipeline".
                    # I will create a `normalize_custom` helper or dynamically call `normalize_{adapter}`.
                    
                    # Dynamic Normalizer Call
                    from us_ats_jobs import normalizer
                    norm_func_name = f"normalize_{adapter_name}"
                    
                    if hasattr(normalizer, norm_func_name):
                        norm_func = getattr(normalizer, norm_func_name)
                        batch_norm = [norm_func(j, name) for j in batch_raw]
                    else:
                        # Fallback: Just try to use raw as is (hoping keys match)
                        logger.warning(f"⚠️ No normalizer found for {adapter_name}. Using raw.", extra=log_context)
                        batch_norm = batch_raw 

                    # Save Normalized FIRST (Parent Table)
                    database.insert_jobs(batch_norm)
                    total_fetched += len(batch_norm)

                    # Save Raw (Child Table)
                    for j_raw, j_norm in zip(batch_raw, batch_norm):
                        curr_id = j_norm.get('job_id') or j_raw.get('id')
                        database.save_raw_job(curr_id, provider, j_raw)
                    
                    # Pagination
                    cursor = adapter.get_next_cursor(None) # Response handled internally
                    if not cursor:
                        break
                        
                    logger.info(f"  📄 Fetched batch. Next cursor: {cursor}", extra=log_context)
                    # Safety Break
                    if total_fetched > 20000:
                        logger.warning("Safety limit reached", extra=log_context)
                        break

                normalized_jobs = [] # We handled insertion inside loop
                raw_jobs = []        # Handled inside loop
                
                # Metrics update outside
                if total_fetched > 0:
                     logger.info(f"✨ Custom Adapter {adapter_name} finished. Total: {total_fetched}", extra=log_context)
                     Monitor.record_success(provider, name, total_fetched, time.time() - start_time)
                     if endpoint_id:
                        database.record_endpoint_result(endpoint_id, True, total_fetched)
                     return True
                else:
                     logger.info("No jobs found via custom adapter", extra=log_context)
                     return True
                     
            except Exception as e:
                logger.error(f"Custom Adapter Error: {e}", extra=log_context)
                raise e

        elif provider == "generic" or provider == "custom":
             # Use full URL
             if not endpoint_url:
                 logger.warning("❌ No URL for generic scrape", extra=log_context)
                 return False
                 
             raw_jobs = fetch_generic_jobs(name, endpoint_url)
             normalized_jobs = [normalize_generic(j, name) for j in raw_jobs]
        
        elif provider in ["generic", "custom", "other"]:
            # Universal Scraper (LLM Based)
            if not endpoint_url:
                raise ValueError("Universal scraper requires endpoint_url")
            normalized_jobs = fetch_universal_jobs(name, endpoint_url)
            
        else:
            logger.warning(f"⚠️  Unknown provider '{provider}' for {endpoint_url}. Trying universal.")
            # Fallback to universal?
            if endpoint_url:
                normalized_jobs = fetch_universal_jobs(name, endpoint_url)
            else:
                raise ValueError(f"Unknown provider '{provider}' and no endpoint_url")

        # 3. Save to DB
        if normalized_jobs:
            logger.info(f"✨ Found {len(normalized_jobs)} jobs", extra=log_context)
            
            # Insert Jobs (Handles creation of job_search records via projection)
            database.insert_jobs(normalized_jobs)
            
            # Record Metrics
            duration = time.time() - start_time
            Monitor.record_success(provider, name, len(normalized_jobs), duration)
            
            # Save Raw Data
            for i, raw in enumerate(raw_jobs):
                if i < len(normalized_jobs):
                     job_id = normalized_jobs[i]['job_id']
                     database.save_raw_job(job_id, provider, raw)
            
            if company_id:
                database.record_company_success(company_id)
            if endpoint_id:
                database.record_endpoint_result(endpoint_id, True, len(normalized_jobs))
            return True
        else:
            logger.info(f"⚠️  No jobs found", extra=log_context)
            if company_id:
                database.record_company_success(company_id)
            if endpoint_id:
                database.record_endpoint_result(endpoint_id, True, 0)
            Monitor.record_success(provider, name, 0, time.time() - start_time)
            return True

    except Exception as e:
        logger.error(f"❌ Error scraping: {str(e)}", extra=log_context)
        Monitor.record_error(provider, name, type(e).__name__)
        
        # Retry Logic
        if retry_count < 2:
            task["retry_count"] = retry_count + 1
            logger.info(f"🔁 Scheduling retry {retry_count + 1}", extra=log_context)
            queue_manager.push_company_task(task)
        else:
            logger.error(f"💀 Max retries reached. Moving to DLQ.", extra=log_context)
            queue_manager.push_to_dlq(task, str(e))
            if company_id:
                database.record_company_failure(company_id)
            if endpoint_id:
                database.record_endpoint_result(endpoint_id, False, 0, str(e))
        
        return False

def worker_loop():
    logger.info("🚀 Worker started. Waiting for tasks...")
    
    while not SHUTDOWN:
        # Update Queue Depth Metric
        stats = queue_manager.get_queue_status()
        if "queue_length" in stats:
            Monitor.set_queue_depth("scrape", stats["queue_length"])
            
        task = queue_manager.pop_company_task(timeout=5)
        if task:
            process_company(task)

    logger.info("👋 Worker stopped.")

if __name__ == "__main__":
    worker_loop()
