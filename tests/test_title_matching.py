
import unittest
import os
import sys

# Add root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from us_ats_jobs.resume.matcher import MatchEngine
from us_ats_jobs.resume.parser import ResumeParser

class TestTitleMatching(unittest.TestCase):
    def setUp(self):
        self.engine = MatchEngine()
        self.parser = ResumeParser()
        
    def test_title_extraction(self):
        """Test that ResumeParser correctly extracts current role"""
        text = """John Doe

Senior Software Engineer
San Francisco, CA

EXPERIENCE
..."""
        role = self.parser._extract_role(text)
        self.assertEqual(role, "Senior Software Engineer")
        
    def test_title_score_boost(self):
        """Test that Title Match improves score"""
        
        # Resume 1: Title Matches Job (Python Dev)
        resume_match = {
            "metadata": {
                "current_role": "Senior Python Developer",
                "years_experience": 5,
                "location": {"country": "United States"}
            },
            "skills": ["Python", "Django", "AWS"]
        }
        
        # Resume 2: Title Mismatch (Java Dev) - same skills to isolate title effect
        resume_mismatch = {
            "metadata": {
                "current_role": "Senior Java Developer",
                "years_experience": 5,
                "location": {"country": "United States"}
            },
            "skills": ["Python", "Django", "AWS"] # Same overlap for control
        }
        
        job = {
            "title": "Senior Python Engineer",
            "tech_languages": "Python,Django,AWS",
            "experience_min": 5,
            "semantic_score": 0.8 # Assume base match
        }
        
        
        # Calculate Scores
        print(f"Model loaded: {self.engine.vector_layer.model is not None}")
        
        score_match = self.engine.score_job(resume_match, job)
        score_mismatch = self.engine.score_job(resume_mismatch, job)
        
        print(f"\nTitle Match Resume Role: {resume_match['metadata']['current_role']}")
        print(f"Title Match Score: {score_match['total_score']}")
        print(f"Breakdown: {score_match['breakdown']}")
        
        print(f"\nTitle Mismatch Resume Role: {resume_mismatch['metadata']['current_role']}")
        print(f"Title Mismatch Score: {score_mismatch['total_score']}")
        print(f"Breakdown: {score_mismatch['breakdown']}")
        
        # Verify Match > Mismatch
        self.assertGreater(score_match['total_score'], score_mismatch['total_score'])
        
        # Verify Title Breakdown
        self.assertGreater(score_match['breakdown']['title'], 95) # Should be 100
        self.assertLess(score_mismatch['breakdown']['title'], 90) # Should be 85 (Strong) but less than Exact

if __name__ == '__main__':
    unittest.main()
