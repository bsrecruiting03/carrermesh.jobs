"""
Skill Graph Expansion Module
==============================

Implements hierarchical skill matching using the implies_skills relationships
from the MIND ontology.

Example:
    User searches for "JavaScript"
    → Also matches jobs requiring: React, Vue, Next.js, TypeScript
    
This significantly improves search recall by finding jobs that require
frameworks/libraries that imply knowledge of the base language.

Author: Intelligence Layer Team
Date: 2026-01-31
"""

import psycopg2
from typing import List, Set, Dict, Tuple
from functools import lru_cache


class SkillGraph:
    """
    Manages skill relationship graph for hierarchical matching.
    
    Uses PostgreSQL recursive queries for efficient graph traversal.
    """
    
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.conn = None
        
        # Cache for frequently queried expansions
        self._expansion_cache = {}
    
    def _get_connection(self):
        """Get or create database connection"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
        return self.conn
    
    def expand_skill_names(self, skill_names: List[str], 
                          max_depth: int = 2) -> List[str]:
        """
        Expand skill names to include implied skills.
        
        Args:
            skill_names: List of canonical skill names to expand
            max_depth: Maximum depth of implies graph to traverse
            
        Returns:
            List of all canonical skill names (original + implied)
            
        Example:
            expand_skill_names(["TypeScript"]) 
            → ["TypeScript", "JavaScript"]
        """
        conn = self._get_connection()
        cur = conn.cursor()
        
        # Use PostgreSQL function for expansion
        cur.execute("""
            SELECT DISTINCT canonical_name
            FROM expand_skill_search(%s::TEXT[])
        """, (skill_names,))
        
        expanded = [row[0] for row in cur.fetchall()]
        cur.close()
        
        return expanded
    
    def expand_skill_ids(self, skill_ids: List[int], 
                        max_depth: int = 2) -> Set[int]:
        """
        Expand skill IDs using implies relationships.
        
        Args:
            skill_ids: List of skill_id values to expand
            max_depth: Maximum depth to traverse
            
        Returns:
            Set of all skill IDs (original + implied)
        """
        if not skill_ids:
            return set()
        
        conn = self._get_connection()
        cur = conn.cursor()
        
        # Use recursive CTE to expand graph
        cur.execute("""
            WITH RECURSIVE skill_expansion AS (
                -- Base case: input skills
                SELECT skill_id, 0 AS depth
                FROM unnest(%s::INTEGER[]) AS skill_id
                
                UNION
                
                -- Recursive: skills implied by current level
                SELECT 
                    s.skill_id,
                    se.depth + 1
                FROM skill_expansion se
                JOIN skills s ON s.skill_id = ANY(
                    (SELECT implies_skills FROM skills WHERE skill_id = se.skill_id)
                )
                WHERE se.depth < %s
            )
            SELECT DISTINCT skill_id FROM skill_expansion
        """, (skill_ids, max_depth))
        
        expanded = {row[0] for row in cur.fetchall()}
        cur.close()
        
        return expanded
    
    def get_parent_skills(self, skill_id: int) -> List[Dict]:
        """
        Get skills that imply this skill (reverse lookup).
        
        Args:
            skill_id: The skill ID to find parents for
            
        Returns:
            List of skill dicts that imply this skill
            
        Example:
            get_parent_skills(js_id)  # where js_id = JavaScript
            → [{name: "TypeScript", ...}, {name: "React", ...}]
        """
        conn = self._get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                skill_id,
                canonical_name,
                skill_type,
                technical_domains
            FROM skills
            WHERE %s = ANY(implies_skills)
        """, (skill_id,))
        
        parents = []
        for row in cur.fetchall():
            parents.append({
                'skill_id': row[0],
                'canonical_name': row[1],
                'skill_type': row[2],
                'technical_domains': row[3]
            })
        
        cur.close()
        return parents
    
    def get_skill_path(self, from_skill_id: int, to_skill_id: int) -> List[str]:
        """
        Find path between two skills in implies graph.
        
        Args:
            from_skill_id: Starting skill
            to_skill_id: Target skill
            
        Returns:
            List of canonical names forming the path, or empty if no path
            
        Example:
            get_skill_path(nextjs_id, js_id)
            → ["Next.js", "React", "JavaScript"]
        """
        conn = self._get_connection()
        cur = conn.cursor()
        
        # Use recursive CTE to find path
        cur.execute("""
            WITH RECURSIVE skill_path AS (
                -- Base: start skill
                SELECT 
                    skill_id,
                    canonical_name,
                    ARRAY[canonical_name] AS path,
                    0 AS depth
                FROM skills
                WHERE skill_id = %s
                
                UNION
                
                -- Recursive: follow implies relationships
                SELECT 
                    s.skill_id,
                    s.canonical_name,
                    sp.path || s.canonical_name,
                    sp.depth + 1
                FROM skill_path sp
                JOIN skills current ON current.skill_id = sp.skill_id
                CROSS JOIN unnest(current.implies_skills) AS implied_id
                JOIN skills s ON s.skill_id = implied_id
                WHERE sp.depth < 5  -- Prevent infinite loops
                  AND s.skill_id NOT IN (SELECT unnest(sp.path))  -- Prevent cycles
            )
            SELECT path 
            FROM skill_path
            WHERE skill_id = %s
            LIMIT 1
        """, (from_skill_id, to_skill_id))
        
        result = cur.fetchone()
        cur.close()
        
        return result[0] if result else []
    
    def get_related_skills(self, skill_id: int, 
                          relation_type: str = 'implies') -> List[Dict]:
        """
        Get related skills with relationship metadata.
        
        Args:
            skill_id: The skill to find relations for
            relation_type: Type of relationship ('implies', 'implied_by', 'same_domain')
            
        Returns:
            List of related skill dicts with relationship info
        """
        conn = self._get_connection()
        cur = conn.cursor()
        
        if relation_type == 'implies':
            # Skills this skill implies (direct children)
            cur.execute("""
                SELECT 
                    s.skill_id,
                    s.canonical_name,
                    s.skill_type,
                    s.technical_domains,
                    'implies' AS relation
                FROM skills current
                CROSS JOIN unnest(current.implies_skills) AS implied_id
                JOIN skills s ON s.skill_id = implied_id
                WHERE current.skill_id = %s
            """, (skill_id,))
            
        elif relation_type == 'implied_by':
            # Skills that imply this skill (parents)
            cur.execute("""
                SELECT 
                    skill_id,
                    canonical_name,
                    skill_type,
                    technical_domains,
                    'implied_by' AS relation
                FROM skills
                WHERE %s = ANY(implies_skills)
            """, (skill_id,))
            
        elif relation_type == 'same_domain':
            # Skills in the same technical domain
            cur.execute("""
                SELECT 
                    s.skill_id,
                    s.canonical_name,
                    s.skill_type,
                    s.technical_domains,
                    'same_domain' AS relation
                FROM skills current
                CROSS JOIN unnest(current.technical_domains) AS domain
                JOIN skills s ON domain = ANY(s.technical_domains)
                WHERE current.skill_id = %s
                  AND s.skill_id != %s
                LIMIT 20
            """, (skill_id, skill_id))
        
        else:
            cur.close()
            return []
        
        related = []
        for row in cur.fetchall():
            related.append({
                'skill_id': row[0],
                'canonical_name': row[1],
                'skill_type': row[2],
                'technical_domains': row[3],
                'relation': row[4]
            })
        
        cur.close()
        return related
    
    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()


# ============================================================================
#Helper Functions for Search Integration
# ============================================================================

def expand_search_skills(skill_names: List[str], db_config: dict) -> List[str]:
    """
    Expand search query skills to include implied skills.
    
    This is the main function used by the search API.
    
    Args:
        skill_names: Skills from user search query
        db_config: Database connection config
        
    Returns:
        Expanded list of skill names
    """
    graph = SkillGraph(db_config)
    
    try:
        return graph.expand_skill_names(skill_names, max_depth=2)
    finally:
        graph.close()


def get_job_skill_expansion(job_skill_ids: List[int], 
                           db_config: dict) -> Set[int]:
    """
    Expand job's required skills to include implied skills.
    
    Used for indexing - store both explicit and implied skills.
    
    Args:
        job_skill_ids: Skills extracted from job description
        db_config: Database connection config
        
    Returns:
        Expanded set of skill IDs
    """
    graph = SkillGraph(db_config)
    
    try:
        return graph.expand_skill_ids(job_skill_ids, max_depth=2)
    finally:
        graph.close()


# ============================================================================
# Usage Example
# ============================================================================

if __name__ == '__main__':
    DB_CONFIG = {
        "host": "localhost",
        "port": 5433,
        "database": "job_board",
        "user": "postgres",
        "password": "postgres"
    }
    
    print("=" * 70)
    print("Skill Graph Expansion Demo")
    print("=" * 70)
    
    graph = SkillGraph(DB_CONFIG)
    
    try:
        # Example 1: Expand TypeScript
        print("\n1. Expanding 'TypeScript':")
        print("-" * 70)
        expanded = graph.expand_skill_names(["TypeScript"])
        print(f"TypeScript → {', '.join(expanded)}")
        
        # Example 2: Expand multiple skills
        print("\n2. Expanding multiple skills:")
        print("-" * 70)
        search_terms = ["React", "PostgreSQL"]
        expanded = graph.expand_skill_names(search_terms)
        print(f"Search: {', '.join(search_terms)}")
        print(f"Expanded: {', '.join(expanded)}")
        
        # Example 3: Get related skills
        print("\n3. Related skills for 'Python':")
        print("-" * 70)
        conn = graph._get_connection()
        cur = conn.cursor()
        cur.execute("SELECT skill_id FROM skills WHERE canonical_name = 'Python'")
        python_id = cur.fetchone()
        cur.close()
        
        if python_id:
            related = graph.get_related_skills(python_id[0], 'same_domain')
            print(f"Found {len(related)} skills in Python's technical domains:")
            for skill in related[:10]:
                print(f"  - {skill['canonical_name']} ({', '.join(skill['skill_type'])})")
        
        print("\n" + "=" * 70)
        
    finally:
        graph.close()
