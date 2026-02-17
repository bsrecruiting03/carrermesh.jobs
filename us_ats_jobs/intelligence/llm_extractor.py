import os
import json
import logging
import time
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from openai import OpenAI
from dotenv import load_dotenv

# Try importing Gemini SDK
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

logger = logging.getLogger("LLMExtractor")

# Envs
# We assume .env is loaded by the main entry point, but we can try to load it just in case
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
dotenv_path = os.path.join(root_dir, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or "openai").lower().strip(' "')

# Configure Keys & Models
if LLM_PROVIDER == "groq":
    groq_keys_str = (os.getenv("GROQ_API_KEYS") or os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY") or "").strip(' "')
    GROQ_API_KEYS = [k.strip() for k in groq_keys_str.split(',') if k.strip()]
    API_KEY = GROQ_API_KEYS[0] if GROQ_API_KEYS else None
    LLM_BASE_URL = "https://api.groq.com/openai/v1"
    LLM_MODEL = (os.getenv("LLM_MODEL") or "llama-3.3-70b-versatile").strip(' "')
elif LLM_PROVIDER == "gemini":
    input_keys = (os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY") or "").strip(' "')
    GEMINI_API_KEYS = [k.strip() for k in input_keys.split(',') if k.strip()]
    API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else None
    LLM_BASE_URL = None
    LLM_MODEL = (os.getenv("LLM_MODEL") or "gemini-flash-latest").strip(' "')
else:
    # Default OpenAI/Compatible
    API_KEY = (os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY") or "").strip(' "')
    LLM_BASE_URL = os.getenv("LLM_BASE_URL") # Might be None for real OpenAI
    LLM_MODEL = (os.getenv("LLM_MODEL") or "gpt-4o-mini").strip(' "')

# Pydantic Models for Structured Output
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
    experience_years: Optional[float] = None
    employment_type: str = "full-time"

class JobListItem(BaseModel):
    title: str
    location: Optional[str] = "Unknown"
    department: Optional[str] = None
    url: Optional[str] = None
    description_snippet: Optional[str] = None

class JobListExtraction(BaseModel):
    jobs: List[JobListItem]

class LLMService:
    def __init__(self):
        self.provider = LLM_PROVIDER
        self.api_keys = []
        self.current_key_index = 0
        
        if self.provider == "groq":
            self.api_keys = GROQ_API_KEYS
            if not self.api_keys:
                logger.warning("⚠️ No Groq API keys found. LLM Service will be disabled.")
                self.client = None
                return
        elif self.provider == "gemini":
            self.api_keys = GEMINI_API_KEYS
            if not self.api_keys:
                logger.warning("⚠️ No Gemini API keys found.")
                self.client = None
                return
        else:
            if not API_KEY:
                logger.warning(f"⚠️ No API Key found for {self.provider}. LLM Service will be disabled.")
                self.client = None
                return
            self.api_keys = [API_KEY]

        self._init_client()

    def _init_client(self):
        current_key = self.api_keys[self.current_key_index]
        if self.provider == "gemini":
            if not HAS_GEMINI:
                logger.error("google-generativeai library not installed.")
                self.client = None
                return
            genai.configure(api_key=current_key)
            self.client = genai.GenerativeModel(
                model_name=LLM_MODEL,
                generation_config={"response_mime_type": "application/json"}
            )
        else:
            self.client = OpenAI(
                api_key=current_key,
                base_url=LLM_BASE_URL
            )

    def rotate_key(self):
        if len(self.api_keys) <= 1:
            # If only 1 key, we can't rotate. Just sleep and retry?
            # Better to handle sleep in the calling loop.
            return False
            
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        logger.info(f"🔄 Rotating to API key #{self.current_key_index + 1}/{len(self.api_keys)}")
        self._init_client()
        return True

    def _init_client(self):
        current_key = self.api_keys[self.current_key_index]
        if self.provider == "gemini":
            if not HAS_GEMINI:
                logger.error("google-generativeai library not installed.")
                self.client = None
                return
            try:
                genai.configure(api_key=current_key)
                self.client = genai.GenerativeModel(
                    model_name=LLM_MODEL,
                    generation_config={"response_mime_type": "application/json"}
                )
            except Exception as e:
                logger.error(f"Failed to init Gemini client: {e}")
                self.client = None
        else:
            self.client = OpenAI(
                api_key=current_key,
                base_url=LLM_BASE_URL
            )

    def extract(self, text: str, title: str, company: str, previous_local_data: Dict = None) -> Optional[JobEnrichmentData]:
        if not self.client:
            return None

        # RATE LIMIT HANDLING
        # Gemini Free Tier: ~15 RPM per key = 1 request every 4 seconds per key.
        # With N keys rotating, we can burst N requests, then must wait for cooldown.
        # 
        # OPTIMIZED STRATEGY:
        # - Base delay of 5s per key (conservative buffer for varying limits)
        # - Divide by number of keys to distribute load
        # - Minimum delay of 0.5s to avoid hammering the API
        
        if self.provider == "gemini":
            base_delay = 5.0  # 5s per key = 12 RPM (safe for all free tiers)
            effective_delay = max(0.5, base_delay / len(self.api_keys))
            time.sleep(effective_delay)

        prompt = f"""You are an expert HR Data Scientist. Extract structured data from this job posting.
Return ONLY valid JSON.

Title: {title}
Company: {company}
Description: {text[:6000]}

REQUIRED JSON STRUCTURE (Extract accurate data):
{{
  "tech_languages": ["Python", "JavaScript"],
  "tech_frameworks": [],
  "tech_tools": [],
  "tech_cloud": [],
  "soft_skills": [],
  "seniority": "mid|senior|junior|lead|principal|staff|Architect|intern|recent_graduate",
  "visa_sponsorship": {{ "mentioned": bool, "confidence": float, "evidence": "string" }},
  "salary": {{ "min": int, "max": int, "currency": "USD", "extracted": bool }},
  "remote_policy": "remote|hybrid|onsite|unspecified",
  "employment_type": "full-time|part-time|contract|internship|temporary|freelance",
  "summary": "Concise 2-sentence summary",
  "experience_years": float
}}
"""
        max_retries = len(self.api_keys) if self.provider == "groq" else 1

        for attempt in range(max_retries):
            try:
                raw_json = ""
                if self.provider == "gemini":
                    response = self.client.generate_content(prompt)
                    raw_json = response.text
                else:
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
                
                return JobEnrichmentData.model_validate_json(raw_json)

            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate_limit" in error_str or "organization_restricted" in error_str:
                    logger.warning(f"⚠️ Rate limit/Restriction on attempt {attempt+1}")
                    if self.rotate_key():
                        continue
                logger.error(f"LLM Extraction Failed: {e}")
                return None
        return None

    def extract_job_list(self, html_content: str, base_url: str) -> List[JobListItem]:
        """
        Extracts a list of jobs from raw HTML content using LLM.
        """
        if not self.client: return []

        # Truncate strictly to avoid token limits (HTML can be huge)
        # Should ideally use a text cleaner first
        clean_text = html_content[:30000] 

        prompt = f"""You are a Web Scraper Agent. Extract job listings from this HTML snippet.
Return a valid JSON object with a list of jobs.

Base URL: {base_url}
Ensure URLs are absolute. If relative, join with Base URL.

REQUIRED JSON STRUCTURE:
{{
  "jobs": [
    {{
      "title": "Software Engineer",
      "location": "New York, NY",
      "department": "Engineering",
      "url": "https://example.com/jobs/123",
      "description_snippet": "We are looking for..."
    }}
  ]
}}

HTML CONTENT:
{clean_text}
"""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                raw_json = ""
                if self.provider == "gemini":
                    # Slow down for rate limits if needed
                    time.sleep(2)
                    response = self.client.generate_content(prompt)
                    raw_json = response.text
                else:
                    response = self.client.chat.completions.create(
                        model=LLM_MODEL,
                        messages=[
                            {"role": "system", "content": "You are a scraper. Output JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        response_format={"type": "json_object"}
                    )
                    raw_json = response.choices[0].message.content
                
                result = JobListExtraction.model_validate_json(raw_json)
                return result.jobs
                
            except Exception as e:
                logger.error(f"LLM Scraping Failed (Attempt {attempt}): {e}")
                if "429" in str(e):
                    time.sleep(5)
                    self.rotate_key()
                    continue
                
                
        return []

    def generate_text(self, prompt: str) -> str:
        """
        Generic text generation (for brainstorming slugs etc).
        """
        if not self.client: return ""
        
        try:
            if self.provider == "gemini":
                response = self.client.generate_content(prompt)
                return response.text
            else:
                response = self.client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            if "429" in str(e):
                self.rotate_key()
            return ""
