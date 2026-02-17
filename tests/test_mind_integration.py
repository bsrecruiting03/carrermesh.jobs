"""
Regression Test Suite for MIND Ontology Integration
=====================================================

Tests skill extraction quality, hierarchical matching, and search improvements.

Usage:
    # Run all tests
    pytest tests/test_mind_integration.py -v
    
    # Run specific test
    pytest tests/test_mind_integration.py::test_skill_extraction -v
    
    # Generate coverage report
    pytest tests/test_mind_integration.py --cov=us_ats_jobs --cov-report=html
"""

import pytest
import psycopg2
from typing import List, Dict

from us_ats_jobs.intelligence.skills_db import SkillExtractorDB, ExtractedSkill
from us_ats_jobs.intelligence.skill_graph import SkillGraph
from api.search_enhanced import HierarchicalJobSearch, SearchQuery


# Test database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "job_board",
    "user": "postgres",
    "password": "postgres"
}


# ============================================================================
# Golden Dataset - Jobs with known expected skills
# ============================================================================

GOLDEN_JOBS = [
    {
        "id": "test_001",
        "title": "Senior Full Stack Developer",
        "description": """
        We're seeking an experienced Full Stack Developer proficient in:
        - Python and TypeScript
        - React and Next.js
        - PostgreSQL and Redis
        - AWS (Lambda, S3, EC2)
        """,
        "expected_skills": {
            "Python", "TypeScript", "React", "Next.js", 
            "PostgreSQL", "Redis", "AWS"
        },
        "implied_skills": {
            "JavaScript",  # Implied by TypeScript, React, Next.js
            "HTML", "CSS"  # Implied by React
        }
    },
    {
        "id": "test_002",
        "title": "Data Engineer",
        "description": """
        Looking for a Data Engineer with:
        - Python (pandas, numpy, scikit-learn)
        - Apache Spark and Airflow
        - SQL and NoSQL databases
        - Experience with ETL pipelines
        """,
        "expected_skills": {
            "Python", "pandas", "NumPy", "scikit-learn",
            "Apache Spark", "Apache Airflow", "SQL"
        },
        "implied_skills": set()
    },
    {
        "id": "test_003",
        "title": "DevOps Engineer",
        "description": """
        DevOps role requiring:
        - Docker and Kubernetes
        - CI/CD with Jenkins or GitLab CI
        - Terraform for Infrastructure as Code
        - Experience with AWS or Azure
        """,
        "expected_skills": {
            "Docker", "Kubernetes", "Jenkins", "Terraform", "AWS"
        },
        "implied_skills": set()
    }
]


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def db_connection():
    """Provide database connection for tests"""
    conn = psycopg2.connect(**DB_CONFIG)
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def skill_extractor():
    """Provide SkillExtractorDB instance"""
    extractor = SkillExtractorDB(DB_CONFIG)
    yield extractor
    extractor.close()


@pytest.fixture(scope="module")
def skill_graph():
    """Provide SkillGraph instance"""
    graph = SkillGraph(DB_CONFIG)
    yield graph
    graph.close()


# ============================================================================
# Skill Extraction Tests
# ============================================================================

class TestSkillExtraction:
    """Tests for skill extraction quality"""
    
    def test_basic_extraction(self, skill_extractor):
        """Test basic skill extraction from text"""
        text = "We need a developer with Python, React, and PostgreSQL experience"
        skills = skill_extractor.extract(text)
        
        skill_names = {s.canonical_name for s in skills}
        
        assert "Python" in skill_names
        assert "React" in skill_names
        assert "PostgreSQL" in skill_names
    
    def test_synonym_matching(self, skill_extractor):
        """Test that synonyms are correctly matched"""
        texts = [
            "Experience with react.js",
            "5+ years of ReactJS",
            "React js framework"
        ]
        
        for text in texts:
            skills = skill_extractor.extract(text)
            skill_names = {s.canonical_name for s in skills}
            assert "React" in skill_names, f"Failed to match in: {text}"
    
    def test_special_characters(self, skill_extractor):
        """Test extraction of skills with special characters"""
        text = "C++, C#, and .NET Core experience required"
        skills = skill_extractor.extract(text)
        
        skill_names = {s.canonical_name for s in skills}
        
        assert "C++" in skill_names
        assert "C#" in skill_names
        assert ".NET" in skill_names or ".NET Core" in skill_names
    
    def test_false_positive_prevention(self, skill_extractor):
        """Test that common words aren't matched as skills"""
        text = """
        We go to work every day with passion.
        Experience in a fast-paced environment is required.
        """
        skills = skill_extractor.extract(text)
        
        # "Go" should not match unless it's clearly the language
        skill_names = {s.canonical_name for s in skills}
        assert "Go" not in skill_names or "Golang" not in skill_names
    
    def test_golden_dataset_precision(self, skill_extractor):
        """Test precision on golden dataset"""
        total_extracted = 0
        total_correct = 0
        
        for job in GOLDEN_JOBS:
            text = f"{job['title']}\n{job['description']}"
            skills = skill_extractor.extract(text)
            skill_names = {s.canonical_name for s in skills}
            
            correct = skill_names & job['expected_skills']
            
            total_extracted += len(skill_names)
            total_correct += len(correct)
        
        precision = total_correct / total_extracted if total_extracted > 0 else 0
        
        # Expect at least 80% precision
        assert precision >= 0.80, f"Precision too low: {precision:.2%}"
    
    def test_golden_dataset_recall(self, skill_extractor):
        """Test recall on golden dataset"""
        total_expected = 0
        total_found = 0
        
        for job in GOLDEN_JOBS:
            text = f"{job['title']}\n{job['description']}"
            skills = skill_extractor.extract(text)
            skill_names = {s.canonical_name for s in skills}
            
            found = skill_names & job['expected_skills']
            
            total_expected += len(job['expected_skills'])
            total_found += len(found)
        
        recall = total_found / total_expected if total_expected > 0 else 0
        
        # Expect at least 85% recall
        assert recall >= 0.85, f"Recall too low: {recall:.2%}"


# ============================================================================
# Skill Graph Tests
# ============================================================================

class TestSkillGraph:
    """Tests for skill relationship graph"""
    
    def test_hierarchical_expansion(self, skill_graph, db_connection):
        """Test that TypeScript expands to include JavaScript"""
        expanded = skill_graph.expand_skill_names(["TypeScript"])
        
        assert "TypeScript" in expanded
        assert "JavaScript" in expanded
    
    def test_framework_expansion(self, skill_graph):
        """Test that frameworks expand to their base languages"""
        expanded = skill_graph.expand_skill_names(["React"])
        
        # React should imply JavaScript
        assert "JavaScript" in expanded
    
    def test_multiple_skill_expansion(self, skill_graph):
        """Test expansion with multiple input skills"""
        expanded = skill_graph.expand_skill_names(["React", "PostgreSQL"])
        
        assert "React" in expanded
        assert "PostgreSQL" in expanded
        # Should also include implied skills
        assert "JavaScript" in expanded
    
    def test_no_circular_dependencies(self, skill_graph, db_connection):
        """Ensure no circular dependency issues in graph"""
        cur = db_connection.cursor()
        
        # Get all skills with implies relationships
        cur.execute("""
            SELECT skill_id, canonical_name, implies_skills
            FROM skills
            WHERE array_length(implies_skills, 1) > 0
            LIMIT 100
        """)
        
        for skill_id, name, implies in cur.fetchall():
            try:
                expanded_ids = skill_graph.expand_skill_ids([skill_id])
                # Should complete without infinite loop
                assert len(expanded_ids) > 0
            except Exception as e:
                pytest.fail(f"Circular dependency detected for {name}: {e}")
        
        cur.close()


# ============================================================================
# Search Enhancement Tests
# ============================================================================

class TestEnhancedSearch:
    """Tests for enhanced job search"""
    
    def test_search_without_expansion(self, db_connection):
        """Baseline: search without skill expansion"""
        search = HierarchicalJobSearch(DB_CONFIG, use_expansion=False)
        
        query = SearchQuery(skills=["JavaScript"])
        results = search.search_jobs(query, limit=100)
        
        baseline_count = len(results)
        search.close()
        
        assert baseline_count >= 0  # Just ensure it runs
    
    def test_search_with_expansion(self, db_connection):
        """Test that expansion increases result count"""
        # Search without expansion
        search_off = HierarchicalJobSearch(DB_CONFIG, use_expansion=False)
        query = SearchQuery(skills=["JavaScript"])
        without_expansion = search_off.search_jobs(query, limit=1000)
        search_off.close()
        
        # Search with expansion
        search_on = HierarchicalJobSearch(DB_CONFIG, use_expansion=True)
        with_expansion = search_on.search_jobs(query, limit=1000)
        search_on.close()
        
        # Expansion should find same or more results
        assert len(with_expansion) >= len(without_expansion)
    
    def test_skill_autocomplete(self):
        """Test skill autocomplete suggestions"""
        search = HierarchicalJobSearch(DB_CONFIG)
        
        suggestions = search.get_search_suggestions("Pyt", limit=10)
        
        assert len(suggestions) > 0
        # Should include "Python"
        names = [s['name'] for s in suggestions]
        assert "Python" in names
        
        search.close()
    
    def test_related_searches(self, skill_graph):
        """Test related skill suggestions"""
        search = HierarchicalJobSearch(DB_CONFIG)
        
        related = search.get_related_searches(["Python"])
        
        # Should have at least some related skills
        assert len(related) > 0
        
        search.close()


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """End-to-end integration tests"""
    
    def test_full_pipeline(self, skill_extractor, db_connection):
        """Test complete pipeline from extraction to search"""
        # Step 1: Extract skills from test job
        job_text = GOLDEN_JOBS[0]['description']
        skills = skill_extractor.extract(job_text)
        
        assert len(skills) > 0
        
        # Step 2: Verify skills are in database
        cur = db_connection.cursor()
        skill_ids = [s.skill_id for s in skills]
        
        cur.execute("""
            SELECT COUNT(*) FROM skills WHERE skill_id = ANY(%s)
        """, (skill_ids,))
        
        count = cur.fetchone()[0]
        assert count == len(skill_ids)
        
        cur.close()
    
    def test_database_consistency(self, db_connection):
        """Test database referential integrity"""
        cur = db_connection.cursor()
        
        # Check no orphaned job_skills
        cur.execute("""
            SELECT COUNT(*)
            FROM job_skills js
            LEFT JOIN skills s ON js.skill_id = s.skill_id
            WHERE s.skill_id IS NULL
        """)
        orphaned_skills = cur.fetchone()[0]
        assert orphaned_skills == 0, "Found orphaned job_skills records"
        
        # Check no orphaned skill_concepts
        cur.execute("""
            SELECT COUNT(*)
            FROM skill_concepts sc
            LEFT JOIN skills s ON sc.skill_id = s.skill_id
            WHERE s.skill_id IS NULL
        """)
        orphaned_concepts = cur.fetchone()[0]
        assert orphaned_concepts == 0, "Found orphaned skill_concepts records"
        
        cur.close()


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Performance benchmarks"""
    
    def test_extraction_speed(self, skill_extractor):
        """Test skill extraction performance"""
        import time
        
        text = " ".join([job['description'] for job in GOLDEN_JOBS] * 10)
        
        start = time.time()
        skills = skill_extractor.extract(text)
        elapsed = time.time() - start
        
        # Should complete in under 1 second
        assert elapsed < 1.0, f"Extraction too slow: {elapsed:.2f}s"
    
    def test_search_latency(self):
        """Test search query latency"""
        import time
        
        search = HierarchicalJobSearch(DB_CONFIG)
        query = SearchQuery(skills=["Python", "JavaScript"])
        
        start = time.time()
        results = search.search_jobs(query, limit=50)
        elapsed = time.time() - start
        
        search.close()
        
        # Should complete in under 200ms
        assert elapsed < 0.2, f"Search too slow: {elapsed*1000:.0f}ms"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
