
import os
import json
import logging
from typing import List, Set, Dict
from flashtext import KeywordProcessor

logger = logging.getLogger("Layer1Extractor")

class Layer1Extractor:
    def __init__(self, ontology_path: str = None):
        # SMART CASING:
        # We set case_sensitive=True to protect "Go", "IT", "C".
        # We will manually add lowercase versions for safe words like "Python" -> "python".
        self.processor = KeywordProcessor(case_sensitive=True)
        self.ontology_path = ontology_path or self._find_ontology_path()
        self.loaded_count = 0
        
        # Ambiguous terms that MUST be case-sensitive (add more as needed)
        self.ambiguous_terms = {
            "Go", "IT", "C", "R", "React", "Vue", "Chef", "Puppet", "Sails", "Ionic", "Electron", "Swing", "Spring", "Ant", "Hive", "Pig"
        }
        
        self._load_ontology()

    def _find_ontology_path(self) -> str:
        # Navigate up from us_ats_jobs/intelligence/extractor_layer1.py
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # Look for MIND folder
        possible_path = os.path.join(base_dir, "MIND-tech-ontology-main", "__aggregated_skills.json")
        if os.path.exists(possible_path):
            return possible_path
        
        # Fallback to internal taxonomy if MIND not found (for robustness)
        logger.warning("⚠️ MIND Ontology not found. Falling back to taxonomy.json")
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "taxonomy.json")

    def _add_skill_smartly(self, word: str, canonical: str):
        """
        Adds a skill to FlashText with smart casing logic.
        """
        if not word: return

        # 1. Always add the exact original casing
        self.processor.add_keyword(word, canonical)
        
        # 2. If it's NOT in the ambiguous list, add the lowercase version too
        # This makes "Python" match "python", but "Go" will NOT match "go".
        if word not in self.ambiguous_terms and word.title() not in self.ambiguous_terms:
            if word != word.lower():
                self.processor.add_keyword(word.lower(), canonical)

    def _load_ontology(self):
        try:
            if not self.ontology_path or not os.path.exists(self.ontology_path):
                logger.error(f"❌ Ontology file missing: {self.ontology_path}")
                return

            logger.info(f"📚 Loading Ontology from {self.ontology_path}...")
            
            with open(self.ontology_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Detect format (MIND Array vs Taxonomy Dict)
            if isinstance(data, list):
                # MIND Ontology Format: [{"name": "Python", "synonyms": [...]}, ...]
                for item in data:
                    canonical = item.get("name")
                    if not canonical: continue
                    
                    # Add canonical
                    self._add_skill_smartly(canonical, canonical)
                    
                    # Add synonyms
                    synonyms = item.get("synonyms") or []
                    if isinstance(synonyms, list):
                        for syn in synonyms:
                            self._add_skill_smartly(syn, canonical)
                    
                    self.loaded_count += 1
                    
            elif isinstance(data, dict):
                # Legacy Taxonomy Format: {"Category": {"Sub": {"Skill": ["Alias"]}}}
                for cat, subcats in data.items():
                    for subcat, skills in subcats.items():
                        for canonical, aliases in skills.items():
                            self._add_skill_smartly(canonical, canonical)
                            for alias in aliases:
                                self._add_skill_smartly(alias, canonical)
                            self.loaded_count += 1

            logger.info(f"✅ Layer 1 Ready: Loaded {self.loaded_count} skills into FlashText (Smart Casing).")

        except Exception as e:
            logger.error(f"❌ Failed to load ontology: {e}")

    def extract(self, text: str) -> List[str]:
        """
        Extracts skills using Aho-Corasick (O(N) complexity).
        Returns a list of unique canonical skill names.
        """
        if not text:
            return []
        
        # FlashText extract_keywords returns list of matching clean names
        found_skills = self.processor.extract_keywords(text)
        
        # Return unique list
        return list(set(found_skills))

# Singleton for easy import
_extractor = None

def extract_skills_fast(text: str) -> List[str]:
    global _extractor
    if _extractor is None:
        _extractor = Layer1Extractor()
    return _extractor.extract(text)

if __name__ == "__main__":
    # Test Block
    print("Testing Layer 1...")
    extractor = Layer1Extractor()
    
    sample_text = "We are looking for a Senior Python Developer with experience in Django, React.js, and Amazon Web Services."
    print(f"\nText: {sample_text}")
    print(f"Extracted: {extractor.extract(sample_text)}")
    
    sample_2 = "Must know Go, C++, and have valid Visa Sponsorship."
    print(f"\nText: {sample_2}")
    print(f"Extracted: {extractor.extract(sample_2)}")
