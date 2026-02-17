
import sys
import os
import logging
import time

# Ensure we can import from app
sys.path.append(os.getcwd())

# Force Provider to Gemini
os.environ["LLM_PROVIDER"] = "gemini"
os.environ["LLM_MODEL"] = "gemini-flash-latest"

try:
    from us_ats_jobs.intelligence.llm_extractor import LLMService, JobEnrichmentData
except ImportError:
    print("❌ Could not import LLMService. Check python path.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GeminiSimpleTest")

def test_gemini_simple():
    logger.info("🚀 Starting Gemini Flash Connectivity Test...")
    
    # 1. Init Service
    try:
        import google.generativeai as genai
        # Configure directly to list models
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY") or os.getenv("LLM_API_KEY"))
        
        logger.info("📋 Listing Available Models:")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                logger.info(f"   - {m.name}")
    except Exception as e:
        logger.error(f"Error listing models: {e}")

    llm_service = LLMService()
    if not llm_service.client:
        logger.error("❌ Failed to initialize Gemini Client (Check API KEY).")
        return

    logger.info(f"✅ Gemini Service Initialized. Model: {os.environ['LLM_MODEL']}")

    # 2. Dummy Job Data
    title = "Senior Python Engineer"
    company = "TechCorp AI"
    description = """
    We are looking for a Senior Python Developer to join our team.
    Salary range: $120,000 - $160,000 USD.
    Must have experience with Django, FastAPI, and AWS.
    Visa sponsorship is available for the right candidate.
    Remote work is possible.
    """
    
    logger.info(f"🔹 Sending prompt for: {title}...")
    
    start_time = time.time()
    try:
        result = llm_service.extract(description, title, company)
        duration = time.time() - start_time
        
        if result:
            logger.info("✅ SUCCESS: Gemini Flash responded!")
            logger.info(f"   ⏱️ Latency: {duration:.2f}s")
            logger.info(f"   💰 Salary: {result.salary.min}-{result.salary.max} {result.salary.currency}")
            logger.info(f"   🛂 Visa: {result.visa_sponsorship.mentioned}")
            logger.info(f"   📝 Summary: {result.summary}")
            logger.info(f"   🧠 Tech: {result.tech_languages}")
        else:
            logger.warning("⚠️ No result returned (None).")

    except Exception as e:
        logger.error(f"❌ Error during extraction: {e}")

if __name__ == "__main__":
    test_gemini_simple()
