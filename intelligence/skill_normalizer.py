
import json
import os
from typing import Dict, List, Optional, Set

class SkillNormalizer:
    """
    Normalizes raw skill names to canonical names using the MIND Ontology.
    
    Flow:
    1. Load __aggregated_skills.json
    2. Build lookup map: {alias.lower(): canonical_name}
    3. Normalize: raw_input -> lookup -> canonical_name
    """
    
    def __init__(self, ontology_path: Optional[str] = None):
        if not ontology_path:
            # Default path relative to this script
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ontology_path = os.path.join(base_dir, "MIND-tech-ontology-main", "__aggregated_skills.json")
            
        self.ontology_path = ontology_path
        self.lookup_map: Dict[str, str] = {}
        self.canonical_set: Set[str] = set()
        self._load_ontology()

    def _load_ontology(self):
        try:
            if not os.path.exists(self.ontology_path):
                print(f"⚠️  Ontology file not found at: {self.ontology_path}")
                return

            with open(self.ontology_path, 'r', encoding='utf-8') as f:
                skills_data = json.load(f)
                
            count = 0
            for skill in skills_data:
                canonical = skill.get('name')
                if not canonical:
                    continue
                    
                self.canonical_set.add(canonical)
                
                # Add canonical itself to map (case-insensitive)
                self.lookup_map[canonical.lower()] = canonical
                
                # Add synonyms
                for synonym in skill.get('synonyms', []):
                    self.lookup_map[synonym.lower()] = canonical
                
                count += 1
                
            print(f"✅ SkillNormalizer loaded {count} skills with {len(self.lookup_map)} aliases.")
            
        except Exception as e:
            print(f"❌ Error loading ontology: {e}")

    def normalize(self, raw_skill: str) -> Optional[str]:
        """
        Returns the canonical name if found, otherwise None.
        """
        if not raw_skill:
            return None
            
        clean_skill = raw_skill.strip().lower()
        
        # 1. Direct Lookup
        if clean_skill in self.lookup_map:
            return self.lookup_map[clean_skill]
            
        return None

    def normalize_list(self, raw_skills: List[str]) -> List[str]:
        """
        Normalizes a list of skills, removing duplicates and Nones.
        Returns a list of unique canonical names.
        """
        normalized = set()
        for s in raw_skills:
            norm = self.normalize(s)
            if norm:
                normalized.add(norm)
            else:
                # OPTIONAL: Keep unknown skills as-is? 
                # For now, let's keep them but maybe flag them?
                # Decision: Keep raw if no match found (Hybrid approach)
                normalized.add(s.strip()) 
        
        return list(normalized)
