"""
Qualifications Extractor
Extracts seniority level, education requirements, certifications, and soft skills from job data.
"""

import re
import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class QualificationsResult:
    seniority_tier: str
    seniority_level: int
    education_level: str
    certifications: List[str]
    soft_skills: List[str]
    
    def to_dict(self):
        return asdict(self)


class QualificationsExtractor:
    def __init__(self, taxonomy_path: Optional[str] = None):
        """Initialize with qualifications taxonomy."""
        if not taxonomy_path:
            base_path = os.path.dirname(os.path.abspath(__file__))
            taxonomy_path = os.path.join(base_path, "qualifications_taxonomy.json")
        
        self.taxonomy = self._load_taxonomy(taxonomy_path)
    
    def _load_taxonomy(self, path: str) -> Dict:
        """Load the qualifications taxonomy from JSON."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading taxonomy: {e}")
            return {}
    
    def extract_seniority_from_title(self, title: str) -> Tuple[str, int]:
        """
        Extract seniority tier from job title.
        Returns (display_name, level) tuple.
        """
        if not title:
            return ("Unknown", 0)
        
        title_lower = title.lower()
        
        # Check from highest to lowest seniority to get the most senior match
        seniority_order = ["c_suite", "executive", "management", "senior", "mid", "junior", "foundational"]
        
        for tier in seniority_order:
            tier_data = self.taxonomy.get("seniority", {}).get(tier, {})
            keywords = tier_data.get("keywords", [])
            
            for keyword in keywords:
                if keyword in title_lower:
                    return (tier_data.get("display", tier), tier_data.get("level", 0))
        
        # Default to mid-level if no match (most common)
        return ("Mid-Level", 3)
    
    def extract_education(self, text: str) -> str:
        """Extract highest education requirement from job description."""
        if not text:
            return "Unknown"
        
        text_lower = text.lower()
        
        # Check from highest to lowest education level
        education_order = ["advanced", "professional", "technical", "introductory"]
        
        for level in education_order:
            level_data = self.taxonomy.get("education", {}).get(level, {})
            keywords = level_data.get("keywords", [])
            
            for keyword in keywords:
                if keyword in text_lower:
                    return level_data.get("display", level)
        
        return "Not Specified"
    
    def extract_certifications(self, text: str) -> List[str]:
        """Extract all certifications mentioned in the text."""
        if not text:
            return []
        
        text_lower = text.lower()
        found_certs = set()
        
        cert_data = self.taxonomy.get("certifications", {})
        
        for provider, levels in cert_data.items():
            for level, keywords in levels.items():
                for keyword in keywords:
                    # Use word boundary matching
                    pattern = rf'\b{re.escape(keyword)}\b'
                    if re.search(pattern, text_lower):
                        # Normalize to display name
                        display_name = self._normalize_cert_name(keyword, provider)
                        found_certs.add(display_name)
        
        return sorted(list(found_certs))
    
    def _normalize_cert_name(self, keyword: str, provider: str) -> str:
        """Convert a matched keyword to a display-friendly certification name."""
        # Map common patterns to clean names
        cert_map = {
            # AWS
            "aws cloud practitioner": "AWS Cloud Practitioner",
            "aws solutions architect": "AWS Solutions Architect",
            "aws developer": "AWS Developer",
            "aws devops": "AWS DevOps Engineer",
            "aws security specialty": "AWS Security Specialty",
            "aws machine learning": "AWS ML Specialty",
            # Azure
            "az-900": "Azure Fundamentals (AZ-900)",
            "az-104": "Azure Administrator (AZ-104)",
            "az-204": "Azure Developer (AZ-204)",
            "az-305": "Azure Solutions Architect (AZ-305)",
            "az-400": "Azure DevOps Engineer (AZ-400)",
            "dp-203": "Azure Data Engineer (DP-203)",
            "ai-102": "Azure AI Engineer (AI-102)",
            # GCP
            "professional cloud architect": "GCP Cloud Architect",
            "professional data engineer": "GCP Data Engineer",
            "associate cloud engineer": "GCP Associate Engineer",
            "cloud digital leader": "GCP Cloud Digital Leader",
            # Others
            "pmp": "PMP",
            "scrum master": "Scrum Master (CSM)",
            "cissp": "CISSP",
            "ccna": "CCNA",
            "cka": "CKA",
            "ckad": "CKAD",
        }
        
        keyword_lower = keyword.lower()
        if keyword_lower in cert_map:
            return cert_map[keyword_lower]
        
        # Default: capitalize the keyword
        return keyword.upper() if len(keyword) <= 6 else keyword.title()
    
    def extract_soft_skills(self, text: str) -> List[str]:
        """Extract soft skills from job description."""
        if not text:
            return []
        
        text_lower = text.lower()
        found_skills = set()
        
        soft_skills_data = self.taxonomy.get("soft_skills", {})
        
        # Map keywords to canonical soft skill names
        skill_canonical = {
            "communication": "Communication",
            "collaboration": "Collaboration",
            "teamwork": "Teamwork",
            "team player": "Teamwork",
            "problem solver": "Problem Solving",
            "analytical": "Analytical Thinking",
            "critical thinking": "Critical Thinking",
            "leadership": "Leadership",
            "mentorship": "Mentorship",
            "mentor": "Mentorship",
            "creative": "Creativity",
            "innovation": "Innovation",
            "adaptability": "Adaptability",
            "flexible": "Flexibility",
            "fast learner": "Quick Learner",
            "quick learner": "Quick Learner",
            "strategic": "Strategic Thinking",
            "decision-making": "Decision Making",
            "work under pressure": "Works Under Pressure",
        }
        
        for domain, keywords in soft_skills_data.items():
            for keyword in keywords:
                pattern = rf'\b{re.escape(keyword)}\b'
                if re.search(pattern, text_lower):
                    # Use canonical name if available
                    canonical = skill_canonical.get(keyword.lower(), keyword.title())
                    found_skills.add(canonical)
        
        return sorted(list(found_skills))
    
    def extract_experience_years(self, text: str) -> Optional[int]:
        """Extract minimum years of experience from description."""
        if not text:
            return None
            
        # Look for patterns like "5+ years", "3-5 years", "at least 2 years"
        # We want the *minimum* required.
        patterns = [
            r'(\d+)(?:\+|\s*\+)?\s*(?:-\s*\d+)?\s*years?',   # "5+ years", "3-5 years"
            r'min(?:imum)?\s*(?:of)?\s*(\d+)\s*years?',       # "minimum 3 years"
            r'at\s*least\s*(\d+)\s*years?'                    # "at least 2 years"
        ]
        
        candidates = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                try:
                    val = int(m)
                    if 0 < val < 20: # Sanity check
                        candidates.append(val)
                except:
                    pass
        
        if candidates:
            return min(candidates) # Conservative estimate
        return None

    def refine_seniority(self, title_tier: str, title_level: int, years: Optional[int]) -> Tuple[str, int]:
        """Refine seniority based on years of experience if title is ambiguous."""
        
        # If title is explicitly high-level (Executive, C-Suite, Management), trust it.
        if title_level >= 5:
            return (title_tier, title_level)
            
        # If years are known, use them to adjust lower-tier titles
        if years is not None:
            if years <= 2:
                # Force Entry Level if < 2 years, unless title says Senior (which would be weird)
                if title_level < 4: 
                    return ("Entry Level", 1)
            elif years <= 4:
                if title_level < 4:
                    return ("Junior", 2) # Or Mid? usually 3-4 is Mid.
            elif years >= 5:
                # If 5+ years, it's likely Senior, even if title is generic "Analyst"
                if title_level < 5:
                    return ("Senior", 4)
            elif years >= 8:
                return ("Staff/Principal", 5)
                
        return (title_tier, title_level)

    def extract_all(self, title: str, description: str) -> QualificationsResult:
        """Extract all qualifications from job title and description."""
        seniority_display, seniority_level = self.extract_seniority_from_title(title)
        
        # Check experience to refine validity
        years = self.extract_experience_years(description)
        seniority_display, seniority_level = self.refine_seniority(seniority_display, seniority_level, years)
        
        education = self.extract_education(description)
        certifications = self.extract_certifications(description)
        soft_skills = self.extract_soft_skills(description)
        
        return QualificationsResult(
            seniority_tier=seniority_display,
            seniority_level=seniority_level,
            education_level=education,
            certifications=certifications,
            soft_skills=soft_skills
        )



# Singleton
_extractor = QualificationsExtractor()

def extract_qualifications(text: str, title: str = "") -> Dict:
    """
    Top-level helper to extract qualifications.
    Now supports passing title for better seniority inference.
    """
    if not text:
        return {}
        
    result = _extractor.extract_all(title=title, description=text)
    
    # Extract raw years for experience
    years = _extractor.extract_experience_years(text)
    
    return {
        "seniority_tier": result.seniority_tier,
        "seniority_level": result.seniority_level,
        "experience_years": years,
        "education_level": result.education_level,
        "certifications": result.certifications, # List[str]
        "soft_skills": result.soft_skills        # List[str]
    }

if __name__ == "__main__":
    # Test the extractor
    extractor = QualificationsExtractor()
    
    test_cases = [
        {
            "title": "Senior Software Engineer",
            "description": "We're looking for a Senior Engineer with 5+ years experience. AWS Solutions Architect certification preferred. Must have a Bachelor's degree in CS. Strong communication and problem-solving skills required."
        },
        {
            "title": "Junior Developer",
            "description": "Entry level position. Bootcamp graduates welcome! We value teamwork and adaptability."
        },
        {
            "title": "VP of Engineering",
            "description": "Executive role requiring MBA or advanced degree. PMP certification required. Must have strategic thinking and leadership abilities."
        },
        {
            "title": "DevOps Engineer",
            "description": "Looking for certified Kubernetes Administrator (CKA) with Azure DevOps (AZ-400) experience. CISSP a plus."
        }
    ]
    
    print("=" * 70)
    print("QUALIFICATIONS EXTRACTOR - TEST SUITE")
    print("=" * 70)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['title']}")
        print("-" * 50)
        
        result = extractor.extract_all(test["title"], test["description"])
        
        print(f"  Seniority: {result.seniority_tier} (Level {result.seniority_level})")
        print(f"  Education: {result.education_level}")
        print(f"  Certifications: {', '.join(result.certifications) if result.certifications else 'None'}")
        print(f"  Soft Skills: {', '.join(result.soft_skills) if result.soft_skills else 'None'}")
    
    print("\n" + "=" * 70)
