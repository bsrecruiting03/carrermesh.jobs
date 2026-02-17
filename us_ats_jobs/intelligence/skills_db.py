"""
Enhanced Skill Extractor using PostgreSQL MIND Ontology
=========================================================

This is an updated version of SkillExtractor that uses the PostgreSQL-based
MIND ontology instead of the flat taxonomy.json file.

Key improvements:
1. Loads skills from database (not JSON)
2. Supports synonym matching via database lookup
3. Returns skill IDs for relationship graph support
4. Maintains backward compatibility with existing code

Author: Intelligence Layer Team
Date: 2026-01-31
"""

import re
import psycopg2
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class ExtractedSkill:
    """Represents a skill extracted from text"""
    skill_id: int
    canonical_name: str
    matched_synonym: str
    category: List[str]        # skill_type from database
    technical_domains: List[str]
    confidence: float = 1.0
    

class SkillExtractorDB:
    """
    Extracts technical skills from job descriptions using PostgreSQL ontology.
    
    This replaces the original SkillExtractor that used taxonomy.json.
    """
    
    def __init__(self, db_config: dict):
        """
        Initialize with database connection.
        
        Args:
            db_config: PostgreSQL connection parameters
        """
        self.db_config = db_config
        self.conn = None
        
        # Cache for skills data
        self._skills_cache = None
        self._synonym_to_skill = None
        self._skill_patterns = None
        
        # Load ontology from database
        self._load_ontology()
    
    def _get_connection(self):
        """Get or create database connection"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
        return self.conn
    
    def _load_ontology(self):
        """Load skills ontology from PostgreSQL"""
        conn = self._get_connection()
        cur = conn.cursor()
        
        # Load all skills with metadata
        cur.execute("""
            SELECT 
                skill_id,
                canonical_name,
                skill_type,
                synonyms,
                technical_domains,
                implies_skills,
                application_tasks
            FROM skills
            ORDER BY canonical_name
        """)
        
        skills = cur.fetchall()
        cur.close()
        
        # Build skill cache
        self._skills_cache = {}
        self._synonym_to_skill = {}
        
        for (skill_id, canonical, types, synonyms, domains, implies, tasks) in skills:
            skill_data = {
                'skill_id': skill_id,
                'canonical_name': canonical,
                'skill_type': types or [],
                'synonyms': synonyms or [],
                'technical_domains': domains or [],
                'implies_skills': implies or [],
                'application_tasks': tasks or []
            }
            
            self._skills_cache[skill_id] = skill_data
            
            # Map canonical name to skill (lowercase)
            self._synonym_to_skill[canonical.lower()] = skill_id
            
            # Map all synonyms to skill (lowercase)
            for synonym in (synonyms or []):
                self._synonym_to_skill[synonym.lower()] = skill_id
        
        print(f"Loaded {len(self._skills_cache)} skills from database")
        print(f"Total searchable terms (including synonyms): {len(self._synonym_to_skill)}")
        
        # Initialize FlashText
        from flashtext import KeywordProcessor
        self._keyword_processor = KeywordProcessor(case_sensitive=False)
        for term, skill_id in self._synonym_to_skill.items():
            # Store skill_id as the clean_name so we get it back
            self._keyword_processor.add_keyword(term, str(skill_id))

        # Build regex patterns (Keep for special cases)
        self._build_patterns()
    
    def _build_patterns(self):
        """Build optimized regex patterns for skill matching"""
        self._skill_patterns = []
        
        # Special cases that need exact patterns (to avoid false positives)
        SPECIAL_CASES = {
            'C++': r'\bC\+\+\b',
            'C#': r'\bC#\b',
            'C': r'(?:\b|(?<=[\s,]))C(?:\b|(?=[\s,/]))',
            '.NET': r'\.NET\b',
            'Go': r'\b(?:Golang|Go(?:\s+language)?)\b',
            'R': r'(?:\b|(?<=[\s,]))R(?:\b|(?=[\s,/]))',
            'Rust': r'\bRust(?:\s+lang)?\b',
        }

        # Whitelist for legitimate short technical terms (2-3 chars)
        SHORT_WHITELIST = {'go', 'c', 'r', 'js', 'ts', 'kt', 'ai', 'ml', 'db', 'ui', 'ux', 'aws', 'gcp', 'sql', 'git'}
        
        # Create patterns for each searchable term
        for term, skill_id in self._synonym_to_skill.items():
            skill_data = self._skills_cache[skill_id]
            canonical = skill_data['canonical_name']
            
            # Filter out very short noisy synonyms
            if len(term) < 3 and term.lower() not in SHORT_WHITELIST:
                # If it's a single letter and not in our whitelist, skip it
                continue
            
            # Check if this needs special handling
            if canonical in SPECIAL_CASES:
                pattern = SPECIAL_CASES[canonical]
            else:
                # Standard word boundary pattern
                term_escaped = re.escape(term)
                pattern = rf'\b{term_escaped}\b'
            
            try:
                compiled_pattern = re.compile(pattern, re.IGNORECASE)
                self._skill_patterns.append({
                    'pattern': compiled_pattern,
                    'term': term,
                    'skill_id': skill_id,
                    'canonical': canonical
                })
            except re.error as e:
                print(f"Warning: Invalid regex pattern for '{term}': {e}")
    
    def extract(self, text: str, expand_implications: bool = True) -> List[ExtractedSkill]:
        """
        Extract skills from text using FlashText (Fast) + Regex (Special Cases).
        
        Args:
            text: Text to extract from
            expand_implications: If True, automatically adds implied parent/related skills
        """
        if not text:
            return []
        
        extracted = {}  # skill_id -> ExtractedSkill
        
        # --- PHASE 1: FlashText ---
        found_ids = self._keyword_processor.extract_keywords(text)
        for skill_id_str in found_ids:
            skill_id = int(skill_id_str)
            if skill_id not in extracted:
                skill_data = self._skills_cache.get(skill_id)
                if not skill_data: continue
                
                extracted[skill_id] = ExtractedSkill(
                    skill_id=skill_id,
                    canonical_name=skill_data['canonical_name'],
                    matched_synonym="ft_match",
                    category=skill_data['skill_type'],
                    technical_domains=skill_data['technical_domains'],
                    confidence=1.0
                )

        # --- PHASE 2: Knowledge Implication Expansion ---
        if expand_implications:
            new_ids = list(extracted.keys())
            added_any = True
            max_depth = 3 # Prevent infinite cycles if ontology is messy
            depth = 0
            
            while added_any and depth < max_depth:
                added_any = False
                current_batch = list(new_ids)
                new_ids = []
                
                for sid in current_batch:
                    implied_ids = self.get_implied_skills(sid)
                    for implied_id in implied_ids:
                        if implied_id not in extracted:
                            implied_data = self._skills_cache.get(implied_id)
                            if implied_data:
                                extracted[implied_id] = ExtractedSkill(
                                    skill_id=implied_id,
                                    canonical_name=implied_data['canonical_name'],
                                    matched_synonym="implication",
                                    category=implied_data['skill_type'],
                                    technical_domains=implied_data['technical_domains'],
                                    confidence=0.8 # Lower confidence for implications
                                )
                                new_ids.append(implied_id)
                                added_any = True
                depth += 1
        
        return list(extracted.values())
    
    def extract_with_context(self, text: str, 
                            context_window: int = 50) -> List[ExtractedSkill]:
        """
        Extract skills with context validation.
        
        This checks surrounding words to reduce false positives.
        
        Args:
            text: Text to extract from
            context_window: Number of characters to check on each side
            
        Returns:
            List of ExtractedSkill objects with confidence scores
        """
        skills = self.extract(text)
        
        # Context-based confidence adjustment
        text_lower = text.lower()
        
        for skill in skills:
            # Find position of match
            match = re.search(
                re.escape(skill.matched_synonym),
                text_lower,
                re.IGNORECASE
            )
            
            if match:
                start = max(0, match.start() - context_window)
                end = min(len(text), match.end() + context_window)
                context = text_lower[start:end]
                
                # Boost confidence if in positive context
                positive_markers = [
                    'experience', 'proficient', 'skilled', 'expert',
                    'knowledge', 'familiar', 'using', 'working with'
                ]
                
                if any(marker in context for marker in positive_markers):
                    skill.confidence = min(1.0, skill.confidence + 0.2)
        
        return skills
    
    def get_skill_by_id(self, skill_id: int) -> Optional[Dict]:
        """Get full skill data by ID"""
        return self._skills_cache.get(skill_id)
    
    def get_skill_by_name(self, name: str) -> Optional[Dict]:
        """Get skill data by canonical name or synonym"""
        skill_id = self._synonym_to_skill.get(name.lower())
        if skill_id:
            return self._skills_cache.get(skill_id)
        return None
    
    def get_implied_skills(self, skill_id: int) -> List[int]:
        """Get list of skill IDs that this skill implies"""
        skill_data = self._skills_cache.get(skill_id)
        if skill_data:
            return skill_data.get('implies_skills', [])
        return []
    
    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()


# ============================================================================
# Helper functions for backward compatibility
# ============================================================================

def extract_tech_stack(text: str, db_config: dict) -> Dict[str, List[str]]:
    """
    Extract tech stack from text (backward compatible interface).
    
    This maintains compatibility with existing code that expects the old format.
    
    Returns:
        Dict with keys: languages, frameworks, cloud, data, other
    """
    extractor = SkillExtractorDB(db_config)
    
    try:
        skills = extractor.extract(text)
        
        # Categorize by technical domain
        result = {
            'languages': [],
            'frameworks': [],
            'cloud': [],
            'data': [],
            'tools': [],
            'other': []
        }
        
        for skill in skills:
            canonical = skill.canonical_name
            
            # Categorize by skill type
            if 'ProgrammingLanguage' in skill.category:
                result['languages'].append(canonical)
            elif 'Framework' in skill.category:
                result['frameworks'].append(canonical)
            elif 'Tool' in skill.category:
                result['tools'].append(canonical)
            elif 'Library' in skill.category:
                # Categorize libraries by domain
                if 'Data Science' in skill.technical_domains or \
                   'Data Engineering' in skill.technical_domains:
                    result['data'].append(canonical)
                else:
                    result['other'].append(canonical)
            else:
                result['other'].append(canonical)
        
        # Remove duplicates
        for key in result:
            result[key] = list(set(result[key]))
        
        return result
        
    finally:
        extractor.close()


def extract_skills_with_ids(text: str, db_config: dict) -> Tuple[List[str], List[int]]:
    """
    Extract skills and return both canonical names and IDs.
    
    Returns:
        Tuple of (canonical_names, skill_ids)
    """
    extractor = SkillExtractorDB(db_config)
    
    try:
        skills = extractor.extract(text)
        
        canonical_names = [s.canonical_name for s in skills]
        skill_ids = [s.skill_id for s in skills]
        
        return canonical_names, skill_ids
        
    finally:
        extractor.close()


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == '__main__':
    # Example usage
    DB_CONFIG = {
        "host": "localhost",
        "port": 5433,
        "database": "job_board",
        "user": "postgres",
        "password": "postgres"
    }
    
    test_text = """
    We're looking for a Senior Full Stack Developer with strong experience in:
    - Python and TypeScript
    - React and Next.js for frontend
    - FastAPI or Django for backend
    - PostgreSQL and Redis
    - AWS (Lambda, S3, RDS)
    - Docker and Kubernetes
    
    Experience with GraphQL and CI/CD pipelines is a plus.
    """
    
    print("Testing enhanced SkillExtractor with database ontology:\n")
    print("=" * 70)
    
    extractor = SkillExtractorDB(DB_CONFIG)
    
    try:
        skills = extractor.extract(test_text)
        
        print(f"\nFound {len(skills)} skills:")
        print("-" * 70)
        
        for skill in skills:
            print(f"✓ {skill.canonical_name:20s} "
                  f"(ID: {skill.skill_id:4d}, "
                  f"matched: '{skill.matched_synonym}', "
                  f"type: {', '.join(skill.category)})")
            
            # Show implied skills
            implied_ids = extractor.get_implied_skills(skill.skill_id)
            if implied_ids:
                implied_names = [
                    extractor.get_skill_by_id(sid)['canonical_name']
                    for sid in implied_ids
                ]
                print(f"   ↳ Implies: {', '.join(implied_names)}")
        
        print("\n" + "=" * 70)
        print("Backward compatible format:")
        print("-" * 70)
        
        tech_stack = extract_tech_stack(test_text, DB_CONFIG)
        for category, items in tech_stack.items():
            if items:
                print(f"{category:15s}: {', '.join(items)}")
        
    finally:
        extractor.close()
