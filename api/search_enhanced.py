"""
Enhanced Job Search with Hierarchical Skill Matching
=====================================================

This module provides search query enhancements using the MIND ontology
skill graph for improved recall.

Key features:
1. Automatic skill expansion (TypeScript → JavaScript)
2. Technical domain-based filtering
3. Concept-based search (e.g., "Authentication" finds all auth-related skills)

Integration points:
- api/database.py::build_job_search_query()
- api/routes.py::search_jobs()

Author: Search Team
Date: 2026-01-31
"""

import psycopg2
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass

from us_ats_jobs.intelligence.skill_graph import SkillGraph


@dataclass
class SearchQuery:
    """Represents a search query with filters"""
    keywords: Optional[str] = None
    skills: List[str] = None
    technical_domains: List[str] = None
    location: Optional[str] = None
    remote: Optional[bool] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    
    def __post_init__(self):
        if self.skills is None:
            self.skills = []
        if self.technical_domains is None:
            self.technical_domains = []


class HierarchicalJobSearch:
    """
    Enhanced job search using MIND ontology skill relationships.
    """
    
    def __init__(self, db_config: dict, use_expansion: bool = True):
        """
        Args:
            db_config: PostgreSQL connection config
            use_expansion: Whether to use hierarchical skill expansion
        """
        self.db_config = db_config
        self.use_expansion = use_expansion
        self.conn = None
        self.skill_graph = SkillGraph(db_config) if use_expansion else None
    
    def _get_connection(self):
        """Get or create database connection"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.db_config)
        return self.conn
    
    def search_jobs(self, query: SearchQuery, 
                   limit: int = 50, offset: int = 0) -> List[Dict]:
        """
        Search jobs with hierarchical skill matching.
        
        Args:
            query: SearchQuery object with filters
            limit: Maximum results to return
            offset: Result offset for pagination
            
        Returns:
            List of job dictionaries with match metadata
        """
        # Expand skills if enabled
        search_skills = query.skills
        if self.use_expansion and search_skills:
            search_skills = self.skill_graph.expand_skill_names(search_skills)
        
        # Build SQL query
        sql, params = self._build_query(query, search_skills, limit, offset)
        
        # Execute
        conn = self._get_connection()
        cur = conn.cursor()
        cur.execute(sql, params)
        
        # Fetch results
        columns = [desc[0] for desc in cur.description]
        results = []
        
        for row in cur.fetchall():
            job_dict = dict(zip(columns, row))
            results.append(job_dict)
        
        cur.close()
        return results
    
    def _build_query(self, query: SearchQuery, expanded_skills: List[str],
                    limit: int, offset: int) -> Tuple[str, List]:
        """Build SQL query with all filters"""
        
        where_clauses = []
        params = []
        param_counter = 1
        
        # Keyword search using full-text search
        if query.keywords:
            where_clauses.append(f"""
                js.search_vector @@ plainto_tsquery('english', ${param_counter})
            """)
            params.append(query.keywords)
            param_counter += 1
        
        # Skill-based search with expansion
        if expanded_skills:
            # Find skill IDs
            skill_ids_subquery = f"""
                SELECT skill_id FROM skills
                WHERE canonical_name = ANY(${param_counter}::TEXT[])
            """
            
            where_clauses.append(f"""
                je.skill_ids && ARRAY(
                    {skill_ids_subquery}
                )
            """)
            params.append(expanded_skills)
            param_counter += 1
        
        # Technical domain filter
        if query.technical_domains:
            where_clauses.append(f"""
                EXISTS (
                    SELECT 1 FROM unnest(je.skill_ids) AS sid
                    JOIN skills s ON s.skill_id = sid
                    WHERE s.technical_domains && ${param_counter}::TEXT[]
                )
            """)
            params.append(query.technical_domains)
            param_counter += 1
        
        # Location filter
        if query.location:
            where_clauses.append(f"j.location ILIKE ${param_counter}")
            params.append(f"%{query.location}%")
            param_counter += 1
        
        # Remote filter
        if query.remote is not None:
            where_clauses.append(f"j.remote_ok = ${param_counter}")
            params.append(query.remote)
            param_counter += 1
        
        # Salary filter
        if query.min_salary:
            where_clauses.append(f"je.min_salary >= ${param_counter}")
            params.append(query.min_salary)
            param_counter += 1
        
        if query.max_salary:
            where_clauses.append(f"je.max_salary <= ${param_counter}")
            params.append(query.max_salary)
            param_counter += 1
        
        # Build final query
        where_clause = " AND ".join(where_clauses) if where_clauses else "TRUE"
        
        sql = f"""
            SELECT 
                j.job_id,
                j.title,
                j.company_name,
                j.location,
                j.remote_ok,
                j.url,
                j.ingested_at,
                je.min_salary,
                je.max_salary,
                je.department,
                je.seniority_level,
                je.skill_ids,
                je.extracted_skill_count,
                ts_rank(js.search_vector, plainto_tsquery('english', ${len(params) + 1})) AS search_rank
            FROM jobs j
            JOIN job_enrichment je ON j.job_id = je.job_id
            JOIN job_search js ON j.job_id = js.job_id
            WHERE {where_clause}
            ORDER BY search_rank DESC, j.ingested_at DESC
            LIMIT ${len(params) + 2}
            OFFSET ${len(params) + 3}
        """
        
        # Add keyword for ranking (use empty string if no keywords)
        params.append(query.keywords or '')
        params.append(limit)
        params.append(offset)
        
        return sql, params
    
    def get_search_suggestions(self, partial_skill: str, limit: int = 10) -> List[Dict]:
        """
        Get skill name suggestions for autocomplete.
        
        Args:
            partial_skill: Partial skill name
            limit: Maximum suggestions
            
        Returns:
            List of skill dicts with metadata
        """
        conn = self._get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                canonical_name,
                skill_type,
                technical_domains,
                (SELECT COUNT(*) FROM job_skills js WHERE js.skill_id = s.skill_id) AS job_count
            FROM skills s
            WHERE 
                canonical_name ILIKE %s
                OR %s = ANY(synonyms)
            ORDER BY job_count DESC
            LIMIT %s
        """, (f"%{partial_skill}%", partial_skill.lower(), limit))
        
        suggestions = []
        for row in cur.fetchall():
            suggestions.append({
                'name': row[0],
                'type': row[1],
                'domains': row[2],
                'job_count': row[3]
            })
        
        cur.close()
        return suggestions
    
    def get_related_searches(self, skill_names: List[str]) -> Dict[str, List[str]]:
        """
        Get related search suggestions based on skill relationships.
        
        Args:
            skill_names: List of skills from current search
            
        Returns:
            Dict with related skill suggestions by relationship type
        """
        if not self.skill_graph:
            return {}
        
        conn = self._get_connection()
        cur = conn.cursor()
        
        # Get skill IDs
        cur.execute("""
            SELECT skill_id, canonical_name
            FROM skills
            WHERE canonical_name = ANY(%s)
        """, (skill_names,))
        
        skill_ids = {name: sid for sid, name in cur.fetchall()}
        
        cur.close()
        
        # Get related skills for each
        related = {
            'implies': set(),
            'implied_by': set(),
            'same_domain': set()
        }
        
        for name, sid in skill_ids.items():
            # Skills this implies (more specific)
            implied = self.skill_graph.get_related_skills(sid, 'implies')
            related['implies'].update(s['canonical_name'] for s in implied)
            
            # Skills that imply this (more general)
            implied_by = self.skill_graph.get_related_skills(sid, 'implied_by')
            related['implied_by'].update(s['canonical_name'] for s in implied_by)
            
            # Same domain skills
            same_domain = self.skill_graph.get_related_skills(sid, 'same_domain')
            related['same_domain'].update(s['canonical_name'] for s in same_domain[:5])
        
        # Convert to lists
        return {k: list(v) for k, v in related.items()}
    
    def close(self):
        """Close connections"""
        if self.skill_graph:
            self.skill_graph.close()
        if self.conn and not self.conn.closed:
            self.conn.close()


# ============================================================================
# API Integration Functions
# ============================================================================

def search_jobs_enhanced(skill_names: List[str] = None,
                        keywords: str = None,
                        location: str = None,
                        db_config: dict = None,
                        use_expansion: bool = True,
                        limit: int = 50,
                        offset: int = 0) -> List[Dict]:
    """
    Convenience function for job search with skill expansion.
    
    This is the main function to use in your API routes.
    """
    query = SearchQuery(
        keywords=keywords,
        skills=skill_names or [],
        location=location
    )
    
    search = HierarchicalJobSearch(db_config, use_expansion=use_expansion)
    
    try:
        return search.search_jobs(query, limit, offset)
    finally:
        search.close()


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
    print("Hierarchical Job Search Demo")
    print("=" * 70)
    
    # Example 1: Search with skill expansion
    print("\n1. Search for 'React' jobs (with expansion):")
    print("-" * 70)
    
    results = search_jobs_enhanced(
        skill_names=["React"],
        db_config=DB_CONFIG,
        use_expansion=True,
        limit=10
    )
    
    print(f"Found {len(results)} jobs")
    for i, job in enumerate(results[:5], 1):
        print(f"{i}. {job['title']} at {job['company_name']}")
        print(f"   Skills: {job.get('extracted_skill_count', 0)} extracted")
    
    # Example 2: Compare with/without expansion
    print("\n2. Comparing expansion ON vs OFF:")
    print("-" * 70)
    
    with_expansion = search_jobs_enhanced(
        skill_names=["JavaScript"],
        db_config=DB_CONFIG,
        use_expansion=True,
        limit=100
    )
    
    without_expansion = search_jobs_enhanced(
        skill_names=["JavaScript"],
        db_config=DB_CONFIG,
        use_expansion=False,
        limit=100
    )
    
    print(f"With expansion: {len(with_expansion)} results")
    print(f"Without expansion: {len(without_expansion)} results")
    print(f"Improvement: +{len(with_expansion) - len(without_expansion)} jobs "
          f"({((len(with_expansion) / len(without_expansion) - 1) * 100):.1f}%)")
