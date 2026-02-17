"""
Skill Intelligence Engine - Core Extraction Logic
Provides production-ready skill extraction and normalization.
Now with comprehensive taxonomy and special-case handling.
"""

import re
import json
import os
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict

@dataclass
class ExtractedSkill:
    canonical_name: str
    category: str
    sub_category: str
    matched_text: str

    def to_dict(self):
        return asdict(self)

# Special cases that need custom regex patterns (single letters, punctuation)
SPECIAL_CASE_PATTERNS = {
    "C": r'\b[Cc]\s+(?:programming|language|code|developer)',
    "C++": r'\b[Cc]\+\+\b',
    "C#": r'\b[Cc]#\b',
    "R": r'\bR\s+(?:programming|language|statistical|studio)\b',
    "Go": r'\b(?:Golang|Go\s+lang(?:uage)?|Go\s+dev(?:eloper)?)\b',  # Strict: Avoid "go to market"
    "Play": r'\bPlay\s+Framework\b',  # Strict: Avoid "role play"
    "Swift": r'\bSwift\s+(?:UI|language|iOS|app)\b', # Avoid "swift action"
    "Rust": r'\bRust\s+(?:lang(?:uage)?|programming|developer)\b', # Avoid "rust" (metal)
    ".NET": r'\.NET\b',
    "Node.js": r'\bNode\.?js\b',
    "Vue.js": r'\bVue\.?js\b',
    "React.js": r'\bReact(?:\.?js|[- ]Native)?\b',
    "Express.js": r'\bExpress\.?js\b',
    "Next.js": r'\bNext\.?js\b',
}


class SkillExtractor:
    def __init__(self, taxonomy_path: Optional[str] = None):
        """Initialize the SkillExtractor with a taxonomy JSON file."""
        if not taxonomy_path:
            base_path = os.path.dirname(os.path.abspath(__file__))
            taxonomy_path = os.path.join(base_path, "taxonomy.json")
            
        self.taxonomy = self._load_taxonomy(taxonomy_path)
        self.alias_to_canonical = self._build_alias_map()
        
        # Sort aliases by length descending for priority matching
        self.sorted_aliases = sorted(self.alias_to_canonical.keys(), key=len, reverse=True)

    def _load_taxonomy(self, path: str) -> Dict:
        """Loads the taxonomy from a JSON file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading taxonomy from {path}: {e}")
            return {}

    def _build_alias_map(self) -> Dict[str, tuple]:
        """Builds a flat map of alias -> (canonical_name, category, sub_category)."""
        alias_map = {}
        for cat, subcats in self.taxonomy.items():
            for subcat, skills in subcats.items():
                for canonical, aliases in skills.items():
                    # Map canonical name itself (case-insensitive)
                    alias_map[canonical.lower()] = (canonical, cat, subcat)
                    # Map all aliases
                    for alias in aliases:
                        alias_map[alias.lower()] = (canonical, cat, subcat)
        return alias_map

    def _extract_special_cases(self, text: str) -> Dict[str, str]:
        """Handle special cases like C, C++, C#, R, etc."""
        found = {}
        for skill_name, pattern in SPECIAL_CASE_PATTERNS.items():
            if re.search(pattern, text, re.IGNORECASE):
                found[skill_name] = skill_name.lower()
        return found

    def extract(self, text: str) -> List[ExtractedSkill]:
        """
        Extracts skills from a text string.
        Uses word-boundary regex for accuracy, with special handling for edge cases.
        """
        if not text:
            return []
            
        text_lower = text.lower()
        extracted = {}
        
        # Step 1: Handle special cases first
        special_matches = self._extract_special_cases(text)
        for canonical, matched in special_matches.items():
            # Look up in taxonomy
            if canonical.lower() in self.alias_to_canonical:
                can, cat, subcat = self.alias_to_canonical[canonical.lower()]
                extracted[can] = ExtractedSkill(
                    canonical_name=can,
                    category=cat,
                    sub_category=subcat,
                    matched_text=matched
                )
        
        # Step 2: Standard extraction for all other skills
        for alias in self.sorted_aliases:
            # Skip if it's a special case (already handled)
            if alias in [k.lower() for k in SPECIAL_CASE_PATTERNS.keys()]:
                continue
                
            # Skip very short aliases to avoid false positives
            if len(alias) < 2:
                continue
            
            # Build pattern with word boundaries
            pattern = rf'(?i)\b{re.escape(alias)}\b'
            
            matches = re.findall(pattern, text_lower)
            if matches:
                canonical, cat, subcat = self.alias_to_canonical[alias]
                
                # Keep only unique canonical skills
                if canonical not in extracted:
                    extracted[canonical] = ExtractedSkill(
                        canonical_name=canonical,
                        category=cat,
                        sub_category=subcat,
                        matched_text=matches[0]
                    )
        
        return list(extracted.values())

    def get_structured_summary(self, skills: List[ExtractedSkill]) -> Dict[str, List[str]]:
        """Groups extracted skills by category for easy display or database storage."""
        summary = {}
        for skill in skills:
            if skill.category not in summary:
                summary[skill.category] = []
            if skill.canonical_name not in summary[skill.category]:
                summary[skill.category].append(skill.canonical_name)
        return summary

    def get_skills_by_category(self, skills: List[ExtractedSkill], category: str) -> List[str]:
        """Returns a list of canonical skill names for a specific category."""
        return [s.canonical_name for s in skills if s.category == category]



# Singleton instance for simple usage
_extractor = SkillExtractor()

def extract_tech_stack(text: str) -> Dict[str, str]:
    """
    Top-level helper to extract tech stack from a job description.
    Returns:
    {
        "languages": "Python, Rust",
        "frameworks": "Django, React",
        ...
    }
    """
    if not text:
        return {}
        
    skills = _extractor.extract(text)
    summary = _extractor.get_structured_summary(skills)
    
    # Flatten for DB storage (comma-separated strings)
    # Categories in taxonomy.json usually: "Languages", "Frameworks", "Cloud", "Data"
    # We map them to the DB columns.
    
    return {
        "languages": ", ".join(summary.get("Languages", [])),
        "frameworks": ", ".join(summary.get("Frameworks", [])),
        "cloud": ", ".join(summary.get("Infrastructure", []) + summary.get("Cloud", [])),
        "data": ", ".join(summary.get("Databases", []) + summary.get("Data", []))
    }

if __name__ == "__main__":
    # Test the extractor
    extractor = SkillExtractor()
    
    test_cases = [
        "Senior Python Developer with Django, PostgreSQL, and AWS experience.",
        "We need a C++ programmer with experience in Unity game development.",
        "Looking for React.js and Node.js developers. TypeScript is a plus.",
        "Data Scientist with PyTorch, TensorFlow, and Jupyter experience.",
        "DevOps engineer familiar with Kubernetes, Terraform, and GitHub Actions.",
        "Full-stack developer: Ruby on Rails backend, Vue.js frontend, MySQL database."
    ]
    
    print("=" * 70)
    print("SKILL EXTRACTOR - TEST SUITE")
    print("=" * 70)
    
    for i, text in enumerate(test_cases, 1):
        print(f"\nTest {i}: {text[:60]}...")
        results = extractor.extract(text)
        summary = extractor.get_structured_summary(results)
        
        for cat, skills in summary.items():
            print(f"  [{cat}]: {', '.join(skills)}")
        
        print(f"  Total: {len(results)} skills")
    
    print("\n" + "=" * 70)
