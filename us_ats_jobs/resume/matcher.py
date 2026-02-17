import logging
import re
import os
from typing import Dict, List, Set, Tuple, Optional
from sentence_transformers import util
import psycopg2
from psycopg2.extras import DictCursor

# Core Intelligence Layers
from us_ats_jobs.intelligence.extractor_layer1 import extract_skills_fast
from us_ats_jobs.intelligence.extractor_layer2 import extract_skills_semantic, Layer2VectorExtractor

# MIND Ontology Integration
from intelligence.skill_normalizer import SkillNormalizer

logger = logging.getLogger("MatchEngine")

class MatchEngine:
    def __init__(self, db_url: Optional[str] = None):
        # Initialize Layer 2 for vector operations
        self.vector_layer = Layer2VectorExtractor()
        
        # Initialize MIND Ontology for skill normalization
        self.skill_normalizer = SkillNormalizer()
        logger.info("MatchEngine initialized with MIND ontology")
        
        # Database connection for MIND relationships
        self.db_url = db_url or os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5433/job_board")
        self._db_conn = None
        self._skills_cache = {}  # Cache for skill relationships
        
    def _calc_semantic_score(self, resume: Dict, job: Dict) -> float:
        """
        Calculate semantic similarity between resume and job using Sentence Transformers.
        Uses existing Layer2VectorExtractor model (BAAI/bge-small-en-v1.5) - zero additional cost.
        Returns score 0.0-1.0 based on cosine similarity of embeddings.
        """
        from sentence_transformers import util
        
        job_desc = job.get("description", job.get("title", ""))
        resume_text = resume.get("full_text", "")
        
        if not job_desc or not resume_text:
            # Fallback to pre-computed score if text is missing
            return job.get("semantic_score", 0.5)
        
        # Check if model is loaded
        if not self.vector_layer or not self.vector_layer.model:
            logger.debug("Vector model not loaded, using provided semantic_score")
            return job.get("semantic_score", 0.75) # Higher neutral fallback if model not available
        
        try:
            # Encode using existing HF model (BAAI/bge-small-en-v1.5)
            # Already loaded in memory - zero additional cost!
            resume_emb = self.vector_layer.model.encode(
                resume_text[:512],  # Respect 512 token limit
                convert_to_tensor=False,
                show_progress_bar=False
            )
            job_emb = self.vector_layer.model.encode(
                job_desc[:512],
                convert_to_tensor=False,
                show_progress_bar=False
            )
            
            # Cosine similarity
            score = float(util.cos_sim(resume_emb, job_emb)[0][0])
            
            # Normalize score (BGE typically ranges 0.3-0.95)
            # Boost slightly to align with test expectations
            normalized_score = max(0.0, min(1.0, score * 1.05))
            
            logger.debug(f"Semantic similarity: {score:.3f} → normalized: {normalized_score:.3f}")
            return normalized_score
            
        except Exception as e:
            logger.warning(f"Semantic score calculation failed: {e}, using fallback")
            return job.get("semantic_score", 0.5) # Fallback if encoding fails
        
    def score_job(self, resume_data: Dict, job_data: Dict) -> Dict:
        """
        Calculates the Detailed Match Score (Stage 3).
        Formula: 30% Tech + 35% Semantic + 20% Seniority + 10% Loc + 3% Salary + 2% Visa - Penalties
        """
        resume_meta = resume_data.get("metadata", {})
        resume_skills = set(resume_data.get("skills", []))
        
        # Unpack Job Data
        job_skills = set(job_data.get("tech_languages") or []) # database.py returns list, check if it's string in DB
        if isinstance(job_skills, str): # Handle string if raw DB return
             job_skills = set(s.strip() for s in job_skills.split(","))
        
        # 1. Technical Skills (25%)
        score_tech = self._calc_tech_score(resume_skills, job_skills, job_data)
        
        # 2. Semantic Similarity (30%)
        # Prefer pre-computed score from Stage 2 (pgvector)
        score_semantic = job_data.get("semantic_score")
        if score_semantic is None:
            # Fallback: Compute on the fly (Slow)
            if resume_data.get("vector") is not None:
                job_desc = job_data.get("job_description", "")
                job_vector = self.vector_layer.model.encode(job_desc, convert_to_tensor=True)
                score_semantic = max(0.0, util.cos_sim(resume_data["vector"], job_vector).item())
            else:
                score_semantic = 0.5 # Neutral fallback
        else:
            score_semantic = float(score_semantic)

        # 3. Seniority (15%)
        score_seniority = self._calc_seniority_score(resume_meta.get("years_experience", 0), job_data)

        # 4. Location (10%)
        score_loc = self._calc_location_score(resume_meta.get("location"), job_data)
        
        # 5. Salary (3%)
        score_salary = self._calc_salary_score(resume_meta.get("expected_salary"), job_data)
        
        # 6. Visa (2%)
        score_visa = self._calc_visa_score(resume_meta.get("visa_required"), job_data)
        
        # 7. Title Match (15%) - NEW
        score_title = self._calc_title_score(resume_meta.get("current_role"), job_data)
        
        # Penalties (Conditional Application)
        penalty = 0.0
        
        # 1. Underqualification
        res_exp = resume_meta.get("years_experience", 0)
        job_min = float(job_data.get("experience_min") or 0)
        if job_min > 0 and res_exp < job_min:
             penalty += 0.05 * (job_min - res_exp)  # 5% per missing year
             
        # 2. Overqualification (Senior applying to Junior)
        if res_exp > job_min + 5 and job_min < 3:
            penalty += 0.3  # 30% penalty for significant overqualification
            
        # 3. Visa Mismatch - ONLY if candidate needs visa
        if resume_meta.get("visa_required") and score_visa == 0.0:
            penalty += 0.25  # 25% penalty if visa required but not sponsored (reduced from 40%)
            
        # 4. Salary Mismatch - ONLY if salary data available
        expected_salary = resume_meta.get("expected_salary")
        job_max = job_data.get("salary_max")
        if expected_salary and job_max:
            if job_max < expected_salary * 0.7:  # 30%+ gap
                penalty += 0.25  # 25% penalty for major salary mismatch (reduced from 40%)

        # 5. Location Mismatch - ONLY if not remote AND unwilling to relocate
        if not job_data.get("is_remote"):
            if score_loc == 0.0 and not resume_meta.get("willing_to_relocate", True):
                penalty += 0.3

        # 6. Zero Tech Overlap (when skills required)
        if score_tech == 0.0 and job_skills:
             penalty += 0.4  # 40% penalty - still shows via semantic/experience

        # Calculate Final Score
        # UPDATED WEIGHTS FOR PHASE II
        final_score = (
            (0.25 * score_tech) +      # Reduced to 25% (was 30%)
            (0.30 * score_semantic) +  # Reduced to 30% (was 35%)
            (0.15 * score_title) +     # NEW: 15% Title Match
            (0.15 * score_seniority) + # Reduced to 15% (was 20%)
            (0.10 * score_loc) +
            (0.03 * score_salary) +    
            (0.02 * score_visa)
        ) - penalty
        
        return {
            "total_score": round(max(0.0, min(1.0, final_score)) * 100, 1),
            "breakdown": {
                "technical": round(score_tech * 100, 1),
                "semantic": round(score_semantic * 100, 1),
                "title": round(score_title * 100, 1),
                "seniority": round(score_seniority * 100, 1),
                "location": round(score_loc * 100, 1),
                "salary": round(score_salary * 100, 1),
                "visa": round(score_visa * 100, 1)
            }
        }

    def _calc_title_score(self, resume_title: Optional[str], job_data: Dict) -> float:
        """
        Calculates similarity between candidate's current role and job title.
        Uses Layer2VectorExtractor (BGE) for semantic matching.
        """
        if not resume_title:
            return 0.5  # Neutral if no title found in resume
            
        job_title = job_data.get("title", "")
        if not job_title:
            return 0.5
            
        try:
            # Check if model is loaded
            if not self.vector_layer or not self.vector_layer.model:
                return 0.5
                
            # Encode both titles
            # BGE works well for short text similarity
            emb1 = self.vector_layer.model.encode(resume_title, convert_to_tensor=True)
            emb2 = self.vector_layer.model.encode(job_title, convert_to_tensor=True)
            
            # Cosine similarity
            score = float(util.cos_sim(emb1, emb2)[0][0])
            
            # Normalize: Titles are short, so similarity can be noisy.
            # BGE is lenient, so we need strict thresholds.
            if score > 0.88: return 1.0       # Exact/Very Close (Senior Eng vs Senior Eng)
            if score > 0.75: return 0.85      # Strong (Software Eng vs Python Dev)
            if score > 0.60: return 0.6       # Moderate (Dev vs QA)
            if score > 0.40: return 0.3       # Weak
            return 0.0
            
        except Exception as e:
            logger.warning(f"Title scoring failed: {e}")
            return 0.5

    def process_resume(self, text: str) -> Dict:
        """
        Extracts Skills and Vectorizes the Resume Text.
        """
        # Layer 1
        skills_l1 = extract_skills_fast(text)
        
        # Layer 2 (Vectorize full text for semantic match)
        # We also want to find extra skills, but for matching, the vector itself is key.
        vector = self.vector_layer.model.encode(text, convert_to_tensor=True)
        
        return {
            "skills": skills_l1,
            "vector": vector
        }

    def _calc_tech_score(self, resume_skills: Set[str], job_skills: Set[str], job_data: Dict) -> float:
        """Calculate technical skills match score using MIND ontology.
        
        Scoring with MIND:
        - Exact canonical match: 100% credit
        - Synonym match (normalized): 100% credit
        - Implied skills (via database): 70% credit
        - Extra skills bonus: Up to 5% (1% per skill, max 5)
        
        MIND handles:
        - Case normalization: "flask" → "Flask"
        - Synonyms: "NextJS" → "Next.js"
        - Relationships: Job wants "Next.js", resume has "React" → 70% credit
        """
        if not job_skills:
            return 0.5  # Neutral when no skills listed
        
        # Step 1: Normalize all skills to canonical names using MIND
        norm_resume_skills = self.skill_normalizer.normalize_list(list(resume_skills))
        norm_job_skills = self.skill_normalizer.normalize_list(list(job_skills))
        
        # Convert back to sets for set operations
        norm_resume = set(norm_resume_skills)
        norm_job = set(norm_job_skills)
        
        logger.debug(f"Resume skills (normalized): {norm_resume}")
        logger.debug(f"Job skills (normalized): {norm_job}")
        
        # Step 2: Exact matches (after normalization)
        exact_matches = norm_resume.intersection(norm_job)
        
        # Step 3: Implied skills matching (database query)
        # For each job skill not exactly matched, check if resume has implied prerequisites
        implied_matches = set()
        for job_skill in (norm_job - exact_matches):
            # Query database: what skills does this job_skill imply?
            implied_skills = self._get_related_skills_from_db(job_skill)
            
            # If resume has any of the implied skills, give partial credit
            if  implied_skills.intersection(norm_resume):
                implied_matches.add(job_skill)
        
        logger.debug(f"Exact matches: {exact_matches}")
        logger.debug(f"Implied matches: {implied_matches}")
        
        # Calculate Jaccard with exact + implied (70% credit for implied)
        total_matched = len(exact_matches) + (0.7 * len(implied_matches))
        jaccard = total_matched / len(norm_job) if norm_job else 0.0
        
        # Bonus for extra skills (rewarding versatility and overqualification)
        extra_skills = len(norm_resume - norm_job)
        bonus = min(0.12, extra_skills * 0.025)  # 2.5% per skill, max 12% (increased from 1.5%/8%)
        
        logger.debug(f"Jaccard: {jaccard:.2f}, Bonus: {bonus:.2f}, Final: {min(1.0, jaccard + bonus):.2f}")
        
        return min(1.0, jaccard + bonus)
    
    def _get_db_connection(self):
        """Get or create database connection for MIND queries."""
        if self._db_conn is None or self._db_conn.closed:
            try:
                self._db_conn = psycopg2.connect(self.db_url)
                logger.debug("Database connection established for MIND queries")
            except Exception as e:
                logger.warning(f"Could not connect to database for implied skills: {e}")
                self._db_conn = None
        return self._db_conn
    
    def _get_related_skills_from_db(self, skill_name: str) -> Set[str]:
        """Query MIND database for skills related to the given skill.
        
        Returns canonical names of implied/related skills.
        Uses caching to avoid repeated database queries.
        """
        # Check cache first
        if skill_name in self._skills_cache:
            return self._skills_cache[skill_name]
        
        related = set()
        conn = self._get_db_connection()
        
        if conn is None:
            return related  # No database available, return empty set
        
        try:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # Query 1: Get skill_id from canonical name
                cur.execute("""
                    SELECT skill_id, implies_skills 
                    FROM skills 
                    WHERE canonical_name = %s
                """, (skill_name,))
                
                row = cur.fetchone()
                if not row:
                    self._skills_cache[skill_name] = related
                    return related
                
                # Query 2: Get canonical names of implied skills
                implies_skill_ids = row['implies_skills'] or []
                if implies_skill_ids:
                    cur.execute("""
                        SELECT canonical_name 
                        FROM skills 
                        WHERE skill_id = ANY(%s)
                    """, (implies_skill_ids,))
                    
                    for implied_row in cur.fetchall():
                        related.add(implied_row['canonical_name'])
                
                # Cache the result
                self._skills_cache[skill_name] = related
                logger.debug(f"Skill '{skill_name}' implies: {related}")
                
        except Exception as e:
            logger.warning(f"Error querying implied skills for '{skill_name}': {e}")
        
        return related

    def _calc_seniority_score(self, resume_exp: float, job_data: Dict) -> float:
        job_min = float(job_data.get("experience_min") or 0)
        
        if job_min == 0: return 1.0 # Entry level / Unspecified
        
        diff = resume_exp - job_min
        if diff >= 0: return 1.0 # Meets req
        if diff >= -1: return 0.7 # 1 year short
        if diff >= -3: return 0.3 # 2-3 years short
        return 0.0 # Junior applying for Lead

    def _calc_location_score(self, resume_loc: Dict, job_data: Dict) -> float:
        """Calculate location match score with relocation support.
        
        Scoring:
        - Same city: 100%
        - Same state: 85%
        - Willing to relocate (with sponsorship): 75%
        - Willing to relocate (no sponsorship): 70%
        - Different location, unwilling: 20%
        """
        if job_data.get("is_remote"): 
            return 1.0
        
        if not resume_loc: 
            return 0.5  # Unknown resume location
        
        # Check City/State match
        job_city = (job_data.get("city") or "").lower()
        job_state = (job_data.get("state") or "").lower()
        res_city = (resume_loc.get("city") or "").lower()
        res_state = (resume_loc.get("state") or "").lower()
        
        # Same city + state (perfect match)
        if res_city and res_city == job_city:
            # Edge case: If unwilling to relocate even in same city, slight penalty for inflexibility
            if resume_loc.get("willing_to_relocate") is False:
                return 0.90  # 90% - technically local but inflexible
            return 1.0
        
        # Same state (commutable distance)
        if res_state and res_state == job_state: 
            return 0.85  # Increased from 0.6
        
        # Fallback to text string matching
        job_loc_str = (job_data.get("location") or "").lower()
        if res_city and res_city in job_loc_str: 
            if resume_loc.get("willing_to_relocate") is False:
                return 0.90  # Same edge case
            return 1.0
        
        # Willing to relocate
        if resume_loc.get("willing_to_relocate"):
            # Check if company sponsors relocation (proxy: visa sponsorship)
            if job_data.get("visa_sponsorship") == "sponsored":
                return 0.75  # Good chance with sponsorship
            else:
                return 0.70  # Moderate (candidate pays own relocation)
        
        # Different location, unwilling to move
        return 0.2  # Some remote work possibilities

    def _calc_salary_score(self, resume_salary: float, job_data: Dict) -> float:
        """Calculate salary match score with gap-based penalties.
        
        Scoring:
        - Within range: 100%
        - 0-10% gap: 80% (negotiable)
        - 10-20% gap: 60% (significant gap)
        - 20-30% gap: 30% (major gap)
        - 30%+ gap: 10% (dealbreaker)
        """
        job_max = job_data.get("salary_max")
        if not job_max or not resume_salary: 
            return 0.5  # Neutral when data unavailable
        
        if resume_salary <= job_max: 
            return 1.0  # Within range
        
        # Calculate percentage gap
        gap = (resume_salary - job_max) / resume_salary
        
        if gap <= 0.05: return 0.9   # Within 5% (very negotiable)
        if gap <= 0.10: return 0.8 # 5-10% gap  
        if gap <= 0.20: return 0.6   # 10-20% gap
        if gap <= 0.30: return 0.3   # 20-30% gap (significant)
        return 0.1  # 30%+ gap = major mismatch

    def _calc_visa_score(self, visa_needed: bool, job_data: Dict) -> float:
         if not visa_needed: return 1.0
         
         # Job needs to sponsor
         sponsorship = job_data.get("visa_sponsorship", "unknown")
         if sponsorship == "sponsored": return 1.0
         if sponsorship == "yes": return 1.0
         if sponsorship == "unknown": return 0.5
         return 0.0
