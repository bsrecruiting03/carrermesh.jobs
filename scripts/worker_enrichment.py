
import sys
import os
import json
import logging
import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor
from openai import OpenAI
from dotenv import load_dotenv

# Add root dir to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from intelligence.skill_normalizer import SkillNormalizer

# Try importing Gemini SDK
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LLMWorker")

# Envs
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
dotenv_path = os.path.join(root_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

DATABASE_URL = os.getenv("DATABASE_URL")
LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "openai").lower().strip(' "')

# Auto-select API key and settings based on provider
if LLM_PROVIDER == "gemini":
    API_KEY = (os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY") or "").strip(' "')
    LLM_BASE_URL = None
    LLM_MODEL = (os.getenv("LLM_MODEL") or "gemini-1.5-flash").strip(' "')
elif LLM_PROVIDER == "grok":
    API_KEY = (os.getenv("GROK_API_KEY") or os.getenv("LLM_API_KEY") or "").strip(' "')
    LLM_BASE_URL = "https://api.x.ai/v1"
    LLM_MODEL = (os.getenv("LLM_MODEL") or "grok-beta").strip(' "')
elif LLM_PROVIDER == "groq":
    # Support multiple Groq API keys for rotation
    groq_keys_str = (os.getenv("GROQ_API_KEYS") or os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY") or "").strip(' "')
    GROQ_API_KEYS = [k.strip(' "') for k in groq_keys_str.split(',') if k.strip()] if groq_keys_str else []
    API_KEY = GROQ_API_KEYS[0] if GROQ_API_KEYS else None  # Start with first key
    LLM_BASE_URL = "https://api.groq.com/openai/v1"
    LLM_MODEL = (os.getenv("LLM_MODEL") or "llama-3.3-70b-versatile").strip(' "')
elif LLM_PROVIDER == "deepseek":
    API_KEY = (os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY") or "").strip(' "')
    LLM_BASE_URL = "https://api.deepseek.com"
    LLM_MODEL = (os.getenv("LLM_MODEL") or "deepseek-chat").strip(' "')
elif LLM_PROVIDER == "ollama":
    API_KEY = "ollama"  # Ollama doesn't validate keys
    LLM_BASE_URL = "http://localhost:11434/v1"
    LLM_MODEL = (os.getenv("LLM_MODEL") or "qwen2.5:7b").strip(' "')
    LLM_MODEL = os.getenv("OLLAMA_MODEL") or os.getenv("LLM_MODEL") or "qwen3:8b"
else:  # Default to OpenAI
    API_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", None)
    LLM_MODEL = os.getenv("LLM_MODEL") or "gpt-4o-mini"



# Initialize Normalizer Globally
try:
    normalizer = SkillNormalizer()
except Exception as e:
    logger.error(f"Failed to initialize SkillNormalizer: {e}")
    normalizer = None

# Exceptions
class APIExhaustedError(Exception):
    """Raised when all configured API keys have hit their rate limits."""
    pass

# Pydantic Models
class VisaSponsorship(BaseModel):
    mentioned: bool
    confidence: float
    evidence: Optional[str] = None

class SalaryData(BaseModel):
    min: Optional[int] = None
    max: Optional[int] = None
    currency: Optional[str] = "USD"
    extracted: bool

class JobEnrichmentData(BaseModel):
    tech_languages: List[str] = Field(default_factory=list)
    tech_frameworks: List[str] = Field(default_factory=list)
    tech_tools: List[str] = Field(default_factory=list)
    tech_cloud: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    seniority: str = "mid"
    visa_sponsorship: VisaSponsorship
    salary: SalaryData
    remote_policy: str = "unspecified"
    summary: str
    experience_years: float = 0.0

class LLMService:
    def __init__(self):
        logger.info(f"Initializing LLM Service. Provider: {LLM_PROVIDER}, Model: {LLM_MODEL}")
        
        self.provider = LLM_PROVIDER
        self.current_key_index = 0
        self.api_keys = []
        
        # Setup API keys (support multiple for Groq)
        if self.provider == "groq" and 'GROQ_API_KEYS' in globals():
            self.api_keys = GROQ_API_KEYS
            if not self.api_keys:
                raise ValueError("No Groq API keys found!")
            logger.info(f"Loaded {len(self.api_keys)} Groq API key(s) for rotation")
            current_key = self.api_keys[0]
        else:
            if not API_KEY:
                logger.error("No API Key found!")
                raise ValueError("Missing API Key")
            current_key = API_KEY
            self.api_keys = [API_KEY]  # Single key
        
        if self.provider == "gemini":
            if not HAS_GEMINI:
                raise ValueError("google-generativeai is not installed. Run pip install google-generativeai")
            genai.configure(api_key=current_key)
            # Ensure model starts with 'models/' if not already present
            model_name = LLM_MODEL if LLM_MODEL.startswith("models/") else f"models/{LLM_MODEL}"
            logger.info(f"Using Gemini Model: {model_name}")
            self.client = genai.GenerativeModel(
                model_name=model_name,
                generation_config={"response_mime_type": "application/json"}
            )
        else:
            # Default to OpenAI Compatible (OpenAI, DeepSeek, Groq, Mistral, Ollama)
            self.client = OpenAI(
                api_key=current_key,
                base_url=LLM_BASE_URL
            )
    
    def rotate_key(self):
        """Rotate to the next API key (for Groq multi-key support)"""
        if len(self.api_keys) <= 1:
            logger.warning("Only one API key available, cannot rotate")
            return False
        
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        new_key = self.api_keys[self.current_key_index]
        
        logger.info(f"🔄 Rotating to API key #{self.current_key_index + 1}/{len(self.api_keys)}")
        
        # Recreate client with new key
        if self.provider == "gemini":
            genai.configure(api_key=new_key)
            model_name = LLM_MODEL if "gemini" in LLM_MODEL else "gemini-1.5-flash"
            self.client = genai.GenerativeModel(
                model_name=model_name,
                generation_config={"response_mime_type": "application/json"}
            )
        else:
            self.client = OpenAI(
                api_key=new_key,
                base_url=LLM_BASE_URL
            )
        return True

    def extract(self, text: str, title: str, company: str) -> Optional[JobEnrichmentData]:
        prompt = f"""You are an expert HR Data Scientist. Extract structured data from this job posting.
Return ONLY valid JSON.

Title: {title}
Company: {company}
Description: {text[:8000]}

REQUIRED JSON STRUCTURE:
{{
  "tech_languages": ["Python", "JavaScript"],
  "tech_frameworks": ["React", "FastAPI"],
  "tech_tools": ["Docker", "Kubernetes"],
  "tech_cloud": ["AWS", "Azure"],
  "soft_skills": ["Leadership", "Communication", "Agile", "Problem Solving"],
  "seniority": "mid|senior|junior|lead|principal",
  "visa_sponsorship": {{
    "mentioned": true|false,
    "confidence": 0-100 (int),
    "evidence": "quote from description or null"
  }},
  "salary": {{
    "min": 120000 (int or null),
    "max": 150000 (int or null),
    "currency": "USD",
    "extracted": true|false
  }},
  "remote_policy": "remote|hybrid|onsite|unspecified",
  "summary": "2-sentence professional summary",
  "experience_years": 0.0 (float)
}}
"""
        
        # Support key rotation on rate limit errors (Groq)
        max_retries = len(self.api_keys) if self.provider == "groq" else 1
        
        for attempt in range(max_retries):
            try:
                raw_json = ""
                
                if self.provider == "gemini":
                    # Google Gemini Call
                    response = self.client.generate_content(prompt)
                    raw_json = response.text
                    
                else:
                    # OpenAI Compatible Call
                    response = self.client.chat.completions.create(
                        model=LLM_MODEL,
                        messages=[
                            {"role": "system", "content": "You are a precise data extraction engine. Output JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.1
                    )
                    raw_json = response.choices[0].message.content
                    
                # Validate with Pydantic
                data = JobEnrichmentData.model_validate_json(raw_json)
                return data
                
            except Exception as e:
                error_str = str(e)
                
                # Check if it's a rate limit error (429) or Restricted (400)
                if "429" in error_str or "rate_limit" in error_str.lower() or "organization_restricted" in error_str.lower():
                    logger.warning(f"⚠️  Rate limit or Restriction hit on attempt {attempt + 1}/{max_retries}")
                    
                    # Try rotating to next key if available
                    if attempt < max_retries - 1:  # Not the last attempt
                        if self.rotate_key():
                            logger.info("Retrying with new API key...")
                            continue  # Retry with new key
                        else:
                            # Rotation failed, re-raise error
                            logger.error(f"LLM Extraction Failed ({self.provider}): {e}")
                            return None
                    else:
                        # Exhausted all keys
                        logger.error(f"❌ All {len(self.api_keys)} API key(s) exhausted. Rate limit on all keys.")
                        raise APIExhaustedError(f"All {self.provider} keys exhausted.")
                else:
                    # Not a rate limit error, propagate immediately
                    logger.error(f"LLM Extraction Failed ({self.provider}): {e}")
                    return None
        
        # Should not reach here
        return None

def process_pending_jobs():
    logger.info("Starting Worker Loop...")
    try:
        llm = LLMService()
    except Exception as e:
        logger.error(f"Fatal Service Init Error: {e}")
        return

    # Database connection management
    while True:
        try:
            conn = psycopg2.connect(DATABASE_URL)
            conn.autocommit = False
            cursor = conn.cursor()
            
            logger.info(f"Connected to DB. Polling for '{LLM_PROVIDER}' jobs...")
            
            while True:
                # Fetch oldest pending job
                cursor.execute("""
                    UPDATE jobs 
                    SET enrichment_status = 'processing'
                    WHERE job_id = (
                        SELECT job_id FROM jobs 
                        WHERE enrichment_status = 'pending'
                        ORDER BY ingested_at DESC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                    )
                    RETURNING job_id, title, company, job_description
                """)
                
                job = cursor.fetchone()
                if not job:
                    conn.commit()
                    time.sleep(5)
                    continue
                
                job_id, title, company, description = job
                t0 = time.time()
                
                try:
                    logger.info(f"Processing Job {job_id}...")
                    desc_text = description or ""
                    
                    enrichment = llm.extract(desc_text, title, company)
                    
                    if enrichment:
                        # Normalize Skills
                        norm_languages = normalizer.normalize_list(enrichment.tech_languages)
                        norm_frameworks = normalizer.normalize_list(enrichment.tech_frameworks)
                        norm_tools = normalizer.normalize_list(enrichment.tech_tools)
                        norm_soft = normalizer.normalize_list(enrichment.soft_skills)

                        cursor.execute("""
                            INSERT INTO job_enrichment (
                                job_id, tech_languages, tech_frameworks, 
                                tech_tools, tech_cloud, seniority, 
                                visa_sponsorship, salary_data, 
                                remote_policy, summary, experience_years,
                                soft_skills,
                                updated_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                            ON CONFLICT (job_id) DO UPDATE SET
                                tech_languages = EXCLUDED.tech_languages,
                                tech_frameworks = EXCLUDED.tech_frameworks,
                                tech_tools = EXCLUDED.tech_tools,
                                tech_cloud = EXCLUDED.tech_cloud,
                                seniority = EXCLUDED.seniority,
                                visa_sponsorship = EXCLUDED.visa_sponsorship,
                                salary_data = EXCLUDED.salary_data,
                                remote_policy = EXCLUDED.remote_policy,
                                summary = EXCLUDED.summary,
                                experience_years = EXCLUDED.experience_years,
                                soft_skills = EXCLUDED.soft_skills,
                                updated_at = NOW()
                        """, (
                            job_id,
                            ', '.join(norm_languages),
                            ', '.join(norm_frameworks),
                            ', '.join(norm_tools),
                            ', '.join(enrichment.tech_cloud),
                            enrichment.seniority,
                            json.dumps(enrichment.visa_sponsorship.model_dump()),
                            json.dumps(enrichment.salary.model_dump()),
                            enrichment.remote_policy,
                            enrichment.summary,
                            enrichment.experience_years,
                            norm_soft
                        ))
                        
                        cursor.execute("""
                            UPDATE jobs 
                            SET enrichment_status = 'completed',
                                error_log = NULL
                            WHERE job_id = %s
                        """, (job_id,))
                        
                        conn.commit()
                        elapsed = time.time() - t0
                        logger.info(f"✓ Enriched {job_id} ({elapsed:.2f}s)")
                    else:
                        raise Exception("LLM returned None")
                        
                except APIExhaustedError as e:
                    # Roll back the job status to pending so it's not lost
                    cursor.execute("UPDATE jobs SET enrichment_status = 'pending' WHERE job_id = %s", (job_id,))
                    conn.commit()
                    logger.error(f"🛑 API QUOTA EXHAUSTED: {e}")
                    logger.error("Pausing worker for 1 hour to wait for quota reset...")
                    time.sleep(3600)  # Pause for 1 hour
                    break  # Break inner loop to reconnect safely later
                except Exception as e:
                    conn.rollback()
                    logger.error(f"Failed to process {job_id}: {e}")
                    try:
                        err_cursor = conn.cursor()
                        err_cursor.execute("""
                            UPDATE jobs 
                            SET enrichment_status = 'failed',
                                error_log = %s
                            WHERE job_id = %s
                        """, (str(e), job_id))
                        conn.commit()
                        err_cursor.close()
                    except:
                        pass
                    
        except Exception as e:
            logger.error(f"Database/Connection Error: {e}. Retrying in 10s...")
            time.sleep(10)
        finally:
            if 'conn' in locals() and conn:
                try:
                    conn.close()
                except:
                    pass

if __name__ == "__main__":
    process_pending_jobs()
