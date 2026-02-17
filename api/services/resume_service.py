import logging
from typing import List, Dict, BinaryIO
from fastapi import UploadFile

from .. import database as db
# Import from the specific paths we created
import sys
import os
# Hack to import from sibling directory 'us_ats_jobs' which is at root level relative to api
# API is at d:/ATS/Main.../api
# Logic is at d:/ATS/Main.../us_ats_jobs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from us_ats_jobs.resume.parser import ResumeParser
from us_ats_jobs.resume.matcher import MatchEngine

logger = logging.getLogger("ResumeService")

class ResumeService:
    def __init__(self):
        self.parser = ResumeParser()
        self.matcher = MatchEngine()
        
    async def match_resume(self, file: UploadFile, limit: int = 20) -> Dict:
        """
        Orchestrates the resume matching process (3-Stage Funnel).
        1. Parse & Embed (Python)
        2. Hard Filter & Vector Search (Postgres)
        3. Detailed Scoring (Python)
        """
        logger.info(f"Processing resume: {file.filename}")
        
        # 1. Parse Resume
        content = await file.read()
        resume_data = self.parser.parse(content, file.filename)
        
        # 2. Extract Vectors & Skills
        processed_resume = self.matcher.process_resume(resume_data["text"])
        
        # Merge data
        full_resume_data = {
            **resume_data,
            **processed_resume
        }
        
        logger.info(f"Resume Parsed. Skills: {len(full_resume_data['skills'])}. Vector Size: {len(full_resume_data['vector'])}")
        
        # 3. Hybrid Search (Stage 1 & 2)
        # Fetch Top 500 candidates using Vector Similarity + Hard Filters
        vector_list = full_resume_data["vector"].tolist() # Convert Tensor to List
        
        # Extract Country from Resume Metadata (Smart Filter)
        resume_location = full_resume_data["metadata"].get("location", {})
        resume_country = resume_location.get("country")
        
        # RELAXATION LOGIC:
        # If candidate is willing to relocate, OR no country found, do not enforce strict country filter.
        # This prevents zero-matches for international candidates or parsing failures.
        strict_country = resume_country
        if resume_location.get("willing_to_relocate"):
            logger.info("Candidate willing to relocate. Disabling strict country filter.")
            strict_country = None
        
        candidate_jobs = db.search_jobs_hybrid(
            embedding=vector_list,
            limit=500, # Stage 2 Limit
            country=strict_country, # Pass strict Country Filter only if needed
            tech_skills=list(full_resume_data["skills"]) # Pass skills (now logging-only in DB)
        )
        
        candidates_found_count = len(candidate_jobs)
        logger.info(f"Hybrid Search (Country: {strict_country}) returned {candidates_found_count} candidates.")
        
        # 4. Detailed Scoring (Stage 3)
        scored_jobs = []
        for job in candidate_jobs:
            score_result = self.matcher.score_job(full_resume_data, job)
            
            # Filter low scores (e.g. < 40%)
            if score_result["total_score"] > 40.0:
                scored_jobs.append({
                    "job": job,
                    "score": score_result
                })
        
        scored_count = len(scored_jobs)
                
        # 5. Sort by Final Score
        scored_jobs.sort(key=lambda x: x["score"]["total_score"], reverse=True)
        
        # 6. Format Response
        top_matches = scored_jobs[:limit]
        
        return {
            "resume_metadata": full_resume_data["metadata"],
            "extracted_skills": full_resume_data["skills"],
            "matches": top_matches,
            "stats": {
                "candidates_found": candidates_found_count,
                "scored_candidates": scored_count,
                "final_matches": len(top_matches)
            }
        }

# Singleton
resume_service = ResumeService()
