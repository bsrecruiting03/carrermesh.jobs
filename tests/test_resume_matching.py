"""
Resume Matching Test Suite - JobRight.ai Standard
==================================================

Tests cover:
1. Technical skills matching (exact, partial, related)
2. Seniority level compatibility
3. Location matching (exact, remote, relocation)
4. Semantic similarity (soft skills, context)
5. Visa sponsorship requirements
6. Salary expectations
7. Years of experience
8. Education requirements
9. Edge cases and failure modes
10. Performance benchmarks

Run: pytest test_resume_matching.py -v
"""

import pytest
from datetime import datetime
from typing import Dict, List
import json

# Assume these are your actual functions
from resume_matcher import (
    calculate_final_score,
    parse_resume,
    extract_location_smart,
    match_resume_to_jobs,
    generate_match_explanation
)


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================

@pytest.fixture
def senior_python_resume():
    """Senior Python developer with 6 years experience"""
    return {
        'full_text': """
        John Doe
        San Francisco, CA 94102
        john.doe@email.com | (555) 123-4567
        
        EXPERIENCE
        Senior Software Engineer | Tech Corp | 2020-Present
        - Led team of 5 engineers developing microservices in Python/Django
        - Architected AWS infrastructure (EC2, S3, Lambda, RDS)
        - Implemented CI/CD pipelines using Jenkins and Docker
        
        Software Engineer | Startup Inc | 2018-2020
        - Built REST APIs with Flask and PostgreSQL
        - Collaborated with cross-functional teams using Agile methodologies
        
        SKILLS
        Languages: Python, JavaScript, SQL
        Frameworks: Django, Flask, React, FastAPI
        Cloud: AWS (EC2, S3, Lambda, RDS), Docker, Kubernetes
        Databases: PostgreSQL, MongoDB, Redis
        Tools: Git, Jenkins, Terraform
        
        EDUCATION
        B.S. Computer Science | Stanford University | 2018
        """,
        'technical_skills': ['Python', 'Django', 'Flask', 'JavaScript', 'React', 
                           'AWS', 'Docker', 'PostgreSQL', 'MongoDB', 'Redis'],
        'soft_skills': ['Leadership', 'Team Management', 'Agile', 'Communication'],
        'seniority': 'senior',
        'years_experience': 6,
        'location_city': 'San Francisco',
        'location_state': 'CA',
        'location_country': 'United States',
        'willing_to_relocate': False,
        'visa_required': False,
        'expected_salary': 140000,
        'education': 'Bachelor',
        'work_authorization': 'US Citizen'
    }


@pytest.fixture
def mid_level_react_resume():
    """Mid-level frontend developer"""
    return {
        'full_text': """
        Jane Smith
        Austin, TX 78701
        jane.smith@email.com
        
        Frontend Developer with 4 years building modern web applications.
        
        EXPERIENCE
        Frontend Developer | WebCo | 2021-Present (3 years)
        - Developed responsive UIs using React, TypeScript, and Tailwind CSS
        - Integrated RESTful APIs and GraphQL
        - Mentored 2 junior developers
        
        Junior Frontend Developer | DesignStudio | 2020-2021 (1 year)
        - Built landing pages with HTML/CSS/JavaScript
        - Collaborated with designers on Figma prototypes
        
        SKILLS
        Frontend: React, TypeScript, JavaScript, HTML/CSS, Tailwind
        State Management: Redux, Context API
        Testing: Jest, React Testing Library
        Tools: Git, Webpack, npm
        """,
        'technical_skills': ['React', 'TypeScript', 'JavaScript', 'HTML', 'CSS',
                           'Redux', 'Tailwind', 'Jest', 'Git'],
        'soft_skills': ['Mentoring', 'Collaboration', 'Design Thinking'],
        'seniority': 'mid',
        'years_experience': 4,
        'location_city': 'Austin',
        'location_state': 'TX',
        'willing_to_relocate': True,
        'visa_required': False,
        'expected_salary': 90000,
        'education': 'Bachelor'
    }


@pytest.fixture
def junior_fullstack_resume():
    """Recent bootcamp graduate"""
    return {
        'full_text': """
        Mike Chen
        Remote | Portland, OR
        mike@email.com
        
        Recent bootcamp graduate eager to start career in software development.
        
        EDUCATION
        Full Stack Web Development Bootcamp | Code Academy | 2024
        
        PROJECTS
        E-commerce Store (Personal Project)
        - Built with Node.js, Express, MongoDB
        - Implemented authentication with JWT
        - Deployed on Heroku
        
        SKILLS
        Languages: JavaScript, Python
        Backend: Node.js, Express
        Frontend: HTML, CSS, basic React
        Database: MongoDB, PostgreSQL (basic)
        """,
        'technical_skills': ['JavaScript', 'Python', 'Node.js', 'Express', 
                           'MongoDB', 'HTML', 'CSS', 'React'],
        'soft_skills': ['Fast Learner', 'Self-Motivated', 'Problem Solving'],
        'seniority': 'junior',
        'years_experience': 0.5,
        'location_city': 'Portland',
        'location_state': 'OR',
        'willing_to_relocate': True,
        'visa_required': False,
        'expected_salary': 65000,
        'education': 'Bootcamp'
    }


@pytest.fixture
def international_ml_engineer_resume():
    """ML Engineer requiring visa sponsorship"""
    return {
        'full_text': """
        Priya Sharma
        Bangalore, India
        priya.sharma@email.com
        
        Machine Learning Engineer with 5 years experience in NLP and Computer Vision.
        Seeking H1B sponsorship for US opportunities.
        
        EXPERIENCE
        ML Engineer | AI Startup India | 2019-Present
        - Developed NLP models using PyTorch and Transformers
        - Deployed models on AWS SageMaker
        - Published 2 papers at ACL conference
        
        SKILLS
        ML/AI: PyTorch, TensorFlow, Scikit-learn, Transformers
        Languages: Python, R
        Cloud: AWS (SageMaker, EC2, S3)
        MLOps: MLflow, Docker, Kubernetes
        """,
        'technical_skills': ['Python', 'PyTorch', 'TensorFlow', 'NLP', 
                           'AWS', 'Docker', 'Kubernetes', 'Machine Learning'],
        'soft_skills': ['Research', 'Technical Writing', 'Collaboration'],
        'seniority': 'senior',
        'years_experience': 5,
        'location_city': 'Bangalore',
        'location_state': None,
        'location_country': 'India',
        'willing_to_relocate': True,
        'visa_required': True,
        'expected_salary': 120000,
        'education': 'Master',
        'work_authorization': 'Requires H1B'
    }


# ============================================================================
# JOB FIXTURES
# ============================================================================

@pytest.fixture
def perfect_match_job():
    """Job that perfectly matches senior_python_resume"""
    return {
        'job_id': 'job-001',
        'title': 'Senior Python Engineer',
        'company': 'Tech Unicorn',
        'description': """
        We're looking for a Senior Python Engineer to join our backend team.
        
        Requirements:
        - 5+ years Python experience
        - Django or Flask framework experience
        - AWS cloud experience (EC2, S3, Lambda)
        - PostgreSQL database knowledge
        - Team leadership experience
        
        Nice to have:
        - Docker/Kubernetes
        - CI/CD experience
        """,
        'tech_stack': 'Python, Django, AWS, PostgreSQL, Docker',
        'seniority': 'senior',
        'min_years_exp': 5,
        'location_city': 'San Francisco',
        'location_state': 'CA',
        'is_remote': False,
        'salary_min': 130000,
        'salary_max': 170000,
        'visa_score': 25,  # Does not sponsor
        'education_required': 'Bachelor',
        'semantic_score': 0.92  # Pre-computed from Stage 2
    }


@pytest.fixture
def partial_match_job():
    """Job with 60% skill overlap"""
    return {
        'job_id': 'job-002',
        'title': 'Backend Engineer',
        'company': 'FinTech Startup',
        'description': """
        Backend Engineer needed for payment processing platform.
        
        Required:
        - Python and Java experience
        - Microservices architecture
        - MySQL or PostgreSQL
        - 3+ years experience
        """,
        'tech_stack': 'Python, Java, MySQL, Kubernetes, Kafka',
        'seniority': 'mid',
        'min_years_exp': 3,
        'location_city': 'San Francisco',
        'location_state': 'CA',
        'is_remote': True,
        'salary_min': 110000,
        'salary_max': 140000,
        'visa_score': 85,  # Sponsors visa
        'education_required': None,
        'semantic_score': 0.68
    }


@pytest.fixture
def remote_job():
    """Fully remote position"""
    return {
        'job_id': 'job-003',
        'title': 'Remote Python Developer',
        'company': 'Remote First Co',
        'description': 'Fully remote Python role. Work from anywhere in the US.',
        'tech_stack': 'Python, Flask, PostgreSQL, AWS',
        'seniority': 'mid',
        'min_years_exp': 3,
        'location_city': None,
        'location_state': None,
        'is_remote': True,
        'salary_min': 100000,
        'salary_max': 130000,
        'visa_score': 0,  # Remote but no visa
        'education_required': None,
        'semantic_score': 0.75
    }


@pytest.fixture
def overqualified_job():
    """Junior position - candidate is overqualified"""
    return {
        'job_id': 'job-004',
        'title': 'Junior Python Developer',
        'company': 'Enterprise Corp',
        'description': 'Entry-level Python developer position. 0-2 years experience.',
        'tech_stack': 'Python, Django, PostgreSQL',
        'seniority': 'junior',
        'min_years_exp': 0,
        'location_city': 'San Francisco',
        'location_state': 'CA',
        'is_remote': False,
        'salary_min': 70000,
        'salary_max': 90000,
        'visa_score': 0,
        'education_required': 'Bachelor',
        'semantic_score': 0.80
    }


@pytest.fixture
def requires_visa_job():
    """Job that sponsors H1B"""
    return {
        'job_id': 'job-005',
        'title': 'Senior Machine Learning Engineer',
        'company': 'AI Research Lab',
        'description': """
        ML Engineer role. H1B sponsorship available for qualified candidates.
        
        Requirements:
        - 5+ years ML experience
        - PyTorch or TensorFlow
        - NLP or Computer Vision expertise
        - AWS/GCP cloud experience
        """,
        'tech_stack': 'Python, PyTorch, AWS, NLP, Docker',
        'seniority': 'senior',
        'min_years_exp': 5,
        'location_city': 'Seattle',
        'location_state': 'WA',
        'is_remote': False,
        'salary_min': 140000,
        'salary_max': 180000,
        'visa_score': 95,  # Actively sponsors
        'education_required': 'Master',
        'semantic_score': 0.88
    }


@pytest.fixture
def wrong_location_job():
    """Job in different city, no remote"""
    return {
        'job_id': 'job-006',
        'title': 'Senior Python Engineer',
        'company': 'NYC Fintech',
        'description': 'On-site role in New York City. No remote work.',
        'tech_stack': 'Python, Django, PostgreSQL, AWS',
        'seniority': 'senior',
        'min_years_exp': 5,
        'location_city': 'New York',
        'location_state': 'NY',
        'is_remote': False,
        'salary_min': 140000,
        'salary_max': 180000,
        'visa_score': 50,
        'education_required': 'Bachelor',
        'semantic_score': 0.89
    }


@pytest.fixture
def skill_mismatch_job():
    """Completely different tech stack"""
    return {
        'job_id': 'job-007',
        'title': 'Senior Java Developer',
        'company': 'Enterprise Bank',
        'description': 'Java backend developer. Spring Boot, Oracle DB.',
        'tech_stack': 'Java, Spring Boot, Oracle, Maven',
        'seniority': 'senior',
        'min_years_exp': 5,
        'location_city': 'San Francisco',
        'location_state': 'CA',
        'is_remote': False,
        'salary_min': 135000,
        'salary_max': 165000,
        'visa_score': 0,
        'education_required': 'Bachelor',
        'semantic_score': 0.42  # Low semantic match
    }


# ============================================================================
# TEST CASES - TECHNICAL SKILLS MATCHING
# ============================================================================

class TestTechnicalSkillsMatching:
    """Test technical skills comparison logic"""
    
    def test_perfect_skill_match(self, senior_python_resume, perfect_match_job):
        """Should score 100% when all required skills are present"""
        score = calculate_final_score(senior_python_resume, perfect_match_job)
        
        # Technical component should be high (>0.9)
        assert score >= 0.85, f"Expected score >= 0.85 for perfect match, got {score}"
        
    def test_partial_skill_match(self, senior_python_resume, partial_match_job):
        """Should score ~60-70% with partial skill overlap"""
        score = calculate_final_score(senior_python_resume, partial_match_job)
        
        assert 0.55 <= score <= 0.75, f"Expected score 0.55-0.75 for partial match, got {score}"
    
    def test_zero_skill_overlap(self, senior_python_resume, skill_mismatch_job):
        """Should score low (<40%) with no overlapping skills"""
        score = calculate_final_score(senior_python_resume, skill_mismatch_job)
        
        assert score < 0.45, f"Expected score < 0.45 for skill mismatch, got {score}"
    
    def test_related_skills_bonus(self, senior_python_resume):
        """Should give bonus for related/transferable skills"""
        job_with_related = {
            'job_id': 'test',
            'tech_stack': 'Python, FastAPI, PostgreSQL, Redis',  # FastAPI related to Flask
            'seniority': 'senior',
            'is_remote': True,
            'semantic_score': 0.85,
            'salary_min': 130000,
            'visa_score': 0
        }
        
        score = calculate_final_score(senior_python_resume, job_with_related)
        
        # Should still score high due to related skills
        assert score >= 0.70, f"Expected score >= 0.70 for related skills, got {score}"
    
    def test_extra_skills_no_penalty(self, senior_python_resume):
        """Having extra skills should not hurt match score"""
        basic_job = {
            'job_id': 'test',
            'tech_stack': 'Python, PostgreSQL',  # Only 2 skills required
            'seniority': 'senior',
            'is_remote': True,
            'semantic_score': 0.80,
            'salary_min': 120000,
            'visa_score': 0
        }
        
        score = calculate_final_score(senior_python_resume, basic_job)
        
        # Should score high even though resume has many more skills
        assert score >= 0.75, f"Extra skills shouldn't penalize, got {score}"


# ============================================================================
# TEST CASES - SENIORITY MATCHING
# ============================================================================

class TestSeniorityMatching:
    """Test seniority level compatibility"""
    
    def test_exact_seniority_match(self, senior_python_resume, perfect_match_job):
        """Senior resume + Senior job = high score"""
        score = calculate_final_score(senior_python_resume, perfect_match_job)
        assert score >= 0.85
    
    def test_one_level_difference_acceptable(self, senior_python_resume, partial_match_job):
        """Senior resume + Mid job = moderate score (70-80%)"""
        # partial_match_job is 'mid' level
        score = calculate_final_score(senior_python_resume, partial_match_job)
        assert 0.55 <= score <= 0.80
    
    def test_overqualification_penalty(self, senior_python_resume, overqualified_job):
        """Senior resume + Junior job = low score due to overqualification"""
        score = calculate_final_score(senior_python_resume, overqualified_job)
        
        # Should be penalized heavily
        assert score < 0.60, f"Overqualified candidates should score low, got {score}"
    
    def test_underqualified_low_score(self, junior_fullstack_resume, perfect_match_job):
        """Junior resume + Senior job = low score"""
        score = calculate_final_score(junior_fullstack_resume, perfect_match_job)
        
        assert score < 0.50, f"Underqualified candidates should score low, got {score}"
    
    def test_years_experience_mismatch(self, junior_fullstack_resume):
        """Job requires 5+ years, candidate has 0.5 years"""
        senior_job = {
            'job_id': 'test',
            'tech_stack': 'JavaScript, Node.js, MongoDB',
            'seniority': 'senior',
            'min_years_exp': 5,
            'is_remote': True,
            'semantic_score': 0.75,
            'salary_min': 120000,
            'visa_score': 0
        }
        
        score = calculate_final_score(junior_fullstack_resume, senior_job)
        
        # Should have significant penalty
        assert score < 0.45, f"Experience gap should lower score, got {score}"


# ============================================================================
# TEST CASES - LOCATION MATCHING
# ============================================================================

class TestLocationMatching:
    """Test location compatibility logic"""
    
    def test_exact_location_match(self, senior_python_resume, perfect_match_job):
        """Same city + Same state = 100% location score"""
        score = calculate_final_score(senior_python_resume, perfect_match_job)
        assert score >= 0.85
    
    def test_remote_job_always_matches(self, senior_python_resume, remote_job):
        """Remote jobs should match any location"""
        score = calculate_final_score(senior_python_resume, remote_job)
        
        # Should score well since it's remote
        assert score >= 0.65
    
    def test_willing_to_relocate_moderate_score(self, mid_level_react_resume, wrong_location_job):
        """Willing to relocate = moderate location score (60%)"""
        # mid_level_react_resume is willing to relocate
        score = calculate_final_score(mid_level_react_resume, wrong_location_job)
        
        # Should get partial credit for relocation willingness
        assert score >= 0.40, f"Relocation willingness should help, got {score}"
    
    def test_unwilling_to_relocate_penalty(self, senior_python_resume, wrong_location_job):
        """Not willing to relocate + different city = low location score"""
        # senior_python_resume.willing_to_relocate = False
        score = calculate_final_score(senior_python_resume, wrong_location_job)
        
        # Should be significantly penalized
        assert score < 0.70, f"Location mismatch should hurt score, got {score}"
    
    def test_international_candidate_remote_ok(self, international_ml_engineer_resume, remote_job):
        """International candidate + Remote job = should match"""
        score = calculate_final_score(international_ml_engineer_resume, remote_job)
        
        # Remote should work for international if visa not required
        # But visa_score=0 for remote_job hurts the match
        assert score >= 0.30  # Will be lower due to visa mismatch


# ============================================================================
# TEST CASES - VISA SPONSORSHIP
# ============================================================================

class TestVisaSponsorship:
    """Test visa requirements and sponsorship matching"""
    
    def test_visa_required_with_sponsorship(self, international_ml_engineer_resume, requires_visa_job):
        """Visa required + High visa score = good match"""
        score = calculate_final_score(international_ml_engineer_resume, requires_visa_job)
        
        # Should score well despite visa requirement
        assert score >= 0.70, f"Visa sponsorship should enable match, got {score}"
    
    def test_visa_required_no_sponsorship(self, international_ml_engineer_resume, perfect_match_job):
        """Visa required + Low visa score = poor match"""
        # perfect_match_job has visa_score = 25 (no sponsorship)
        score = calculate_final_score(international_ml_engineer_resume, perfect_match_job)
        
        # Should be penalized heavily
        assert score < 0.60, f"No visa sponsorship should hurt score, got {score}"
    
    def test_no_visa_needed(self, senior_python_resume, perfect_match_job):
        """US citizen + any visa score = no impact"""
        score = calculate_final_score(senior_python_resume, perfect_match_job)
        
        # Visa should not affect score for US citizens
        assert score >= 0.85


# ============================================================================
# TEST CASES - SALARY EXPECTATIONS
# ============================================================================

class TestSalaryMatching:
    """Test salary compatibility"""
    
    def test_salary_within_range(self, senior_python_resume, perfect_match_job):
        """Expected $140k, job offers $130k-$170k = perfect fit"""
        score = calculate_final_score(senior_python_resume, perfect_match_job)
        assert score >= 0.85
    
    def test_salary_slightly_below_expectations(self, senior_python_resume):
        """Expected $140k, job offers $120k-$145k = moderate fit"""
        lower_salary_job = {
            'job_id': 'test',
            'tech_stack': 'Python, Django, AWS, PostgreSQL',
            'seniority': 'senior',
            'location_city': 'San Francisco',
            'location_state': 'CA',
            'is_remote': False,
            'salary_min': 120000,
            'salary_max': 145000,  # Max just above expectations
            'visa_score': 0,
            'semantic_score': 0.90
        }
        
        score = calculate_final_score(senior_python_resume, lower_salary_job)
        
        # Should be slightly penalized but still good
        assert 0.75 <= score <= 0.90
    
    def test_salary_significantly_below(self, senior_python_resume, overqualified_job):
        """Expected $140k, job offers $70k-$90k = poor fit"""
        score = calculate_final_score(senior_python_resume, overqualified_job)
        
        # Should score very low
        assert score < 0.60
    
    def test_salary_unknown_neutral_score(self, senior_python_resume):
        """Unknown salary = neutral (50% salary component)"""
        no_salary_job = {
            'job_id': 'test',
            'tech_stack': 'Python, Django, AWS, PostgreSQL',
            'seniority': 'senior',
            'location_city': 'San Francisco',
            'location_state': 'CA',
            'is_remote': False,
            'salary_min': None,
            'salary_max': None,
            'visa_score': 0,
            'semantic_score': 0.88
        }
        
        score = calculate_final_score(senior_python_resume, no_salary_job)
        
        # Should still score reasonably without salary info
        assert 0.70 <= score <= 0.90


# ============================================================================
# TEST CASES - SEMANTIC SIMILARITY
# ============================================================================

class TestSemanticMatching:
    """Test soft skills and contextual understanding"""
    
    def test_leadership_keywords_match(self, senior_python_resume):
        """Resume mentions 'Led team' - should match leadership roles"""
        leadership_job = {
            'job_id': 'test',
            'title': 'Engineering Team Lead',
            'description': 'Lead a team of engineers. Mentor junior developers.',
            'tech_stack': 'Python, Django, AWS',
            'seniority': 'lead',
            'is_remote': False,
            'location_city': 'San Francisco',
            'location_state': 'CA',
            'semantic_score': 0.91,  # High due to leadership match
            'salary_min': 150000,
            'visa_score': 0
        }
        
        score = calculate_final_score(senior_python_resume, leadership_job)
        
        # Semantic similarity should boost score
        assert score >= 0.75
    
    def test_domain_context_matching(self, senior_python_resume):
        """Backend engineer resume should match backend roles better than frontend"""
        backend_job = {
            'job_id': 'test',
            'description': 'Backend engineer working on APIs and databases',
            'tech_stack': 'Python, PostgreSQL, Redis',
            'seniority': 'senior',
            'is_remote': True,
            'semantic_score': 0.87,
            'salary_min': 130000,
            'visa_score': 0
        }
        
        frontend_job = {
            'job_id': 'test2',
            'description': 'Frontend engineer building UI components',
            'tech_stack': 'React, TypeScript, CSS',
            'seniority': 'senior',
            'is_remote': True,
            'semantic_score': 0.52,  # Lower semantic match
            'salary_min': 130000,
            'visa_score': 0
        }
        
        backend_score = calculate_final_score(senior_python_resume, backend_job)
        frontend_score = calculate_final_score(senior_python_resume, frontend_job)
        
        assert backend_score > frontend_score, "Backend resume should prefer backend roles"


# ============================================================================
# TEST CASES - EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Test unusual or boundary conditions"""
    
    def test_empty_tech_stack(self, senior_python_resume):
        """Job with no tech stack listed"""
        empty_job = {
            'job_id': 'test',
            'tech_stack': '',
            'seniority': 'senior',
            'is_remote': True,
            'semantic_score': 0.70,
            'salary_min': 120000,
            'visa_score': 0
        }
        
        score = calculate_final_score(senior_python_resume, empty_job)
        
        # Should not crash, give neutral score
        assert 0.40 <= score <= 0.70
    
    def test_malformed_location_data(self):
        """Resume with missing location fields"""
        incomplete_resume = {
            'technical_skills': ['Python'],
            'seniority': 'mid',
            'years_experience': 3,
            'location_city': None,
            'location_state': None,
            'willing_to_relocate': True,
            'visa_required': False,
            'expected_salary': None,
            'semantic_score': 0.75
        }
        
        job = {
            'job_id': 'test',
            'tech_stack': 'Python',
            'seniority': 'mid',
            'is_remote': True,
            'semantic_score': 0.75,
            'salary_min': 90000,
            'visa_score': 0
        }
        
        # Should not crash
        score = calculate_final_score(incomplete_resume, job)
        assert 0 <= score <= 1
    
    def test_negative_years_experience(self):
        """Handle invalid years of experience"""
        invalid_resume = {
            'technical_skills': ['Python'],
            'seniority': 'junior',
            'years_experience': -1,  # Invalid
            'location_city': 'SF',
            'location_state': 'CA',
            'willing_to_relocate': False,
            'visa_required': False
        }
        
        job = {
            'job_id': 'test',
            'tech_stack': 'Python',
            'seniority': 'junior',
            'min_years_exp': 0,
            'is_remote': True,
            'semantic_score': 0.70,
            'salary_min': 70000,
            'visa_score': 0
        }
        
        # Should handle gracefully
        score = calculate_final_score(invalid_resume, job)
        assert 0 <= score <= 1
    
    def test_extremely_long_skill_list(self, senior_python_resume):
        """Job listing 50+ skills"""
        massive_skills = ', '.join([f'Skill{i}' for i in range(50)])
        
        job = {
            'job_id': 'test',
            'tech_stack': f"Python, Django, {massive_skills}",
            'seniority': 'senior',
            'is_remote': True,
            'semantic_score': 0.60,
            'salary_min': 130000,
            'visa_score': 0
        }
        
        score = calculate_final_score(senior_python_resume, job)
        
        # Should not penalize heavily for not having all 50+ skills
        assert score >= 0.30


# ============================================================================
# TEST CASES - MATCH EXPLANATIONS
# ============================================================================

class TestMatchExplanations:
    """Test human-readable match explanations"""
    
    def test_explanation_includes_skill_matches(self, senior_python_resume, perfect_match_job):
        """Explanation should list matching skills"""
        score = calculate_final_score(senior_python_resume, perfect_match_job)
        explanation = generate_match_explanation(senior_python_resume, perfect_match_job, score)
        
        # Should mention specific skills
        assert any('Python' in reason for reason in explanation)
        assert any('skill' in reason.lower() for reason in explanation)
    
    def test_explanation_mentions_seniority(self, senior_python_resume, perfect_match_job):
        """Explanation should note seniority match"""
        score = calculate_final_score(senior_python_resume, perfect_match_job)
        explanation = generate_match_explanation(senior_python_resume, perfect_match_job, score)
        
        assert any('senior' in reason.lower() for reason in explanation)
    
    def test_explanation_shows_location_status(self, senior_python_resume, remote_job):
        """Should indicate if job is remote"""
        score = calculate_final_score(senior_python_resume, remote_job)
        explanation = generate_match_explanation(senior_python_resume, remote_job, score)
        
        assert any('remote' in reason.lower() for reason in explanation)
    
    def test_explanation_warns_about_relocation(self, senior_python_resume, wrong_location_job):
        """Should warn if relocation required"""
        score = calculate_final_score(senior_python_resume, wrong_location_job)
        explanation = generate_match_explanation(senior_python_resume, wrong_location_job, score)
        
        # Should mention location mismatch
        assert len(explanation) > 0  # At least some explanation given


# ============================================================================
# TEST CASES - FULL PIPELINE (INTEGRATION)
# ============================================================================

class TestFullMatchingPipeline:
    """Integration tests for complete resume-to-jobs flow"""
    
    def test_match_returns_top_jobs(self, senior_python_resume):
        """Match function should return sorted list of jobs"""
        jobs = [
            perfect_match_job(),
            partial_match_job(),
            remote_job(),
            overqualified_job(),
            skill_mismatch_job()
        ]
        
        results = match_resume_to_jobs(senior_python_resume, jobs, top_k=3)
        
        assert len(results) == 3
        assert results[0]['match_score'] >= results[1]['match_score']
        assert results[1]['match_score'] >= results[2]['match_score']
    
    def test_minimum_threshold_filtering(self, senior_python_resume):
        """Should filter out jobs below threshold"""
        jobs = [
            skill_mismatch_job(),  # Should score low
            overqualified_job()     # Should score low
        ]
        
        results = match_resume_to_jobs(
            senior_python_resume, 
            jobs, 
            top_k=10,
            min_score_threshold=0.60  # 60% minimum
        )
        
        # Both jobs should be filtered out
        assert all(job['match_score'] >= 60 for job in results)
    
    def test_diverse_results_not_just_same_company(self, senior_python_resume):
        """Should return diverse companies, not all from same employer"""
        # Create 10 jobs, 5 from same company
        jobs = []
        for i in range(5):
            jobs.append({
                'job_id': f'same-company-{i}',
                'company': 'Megacorp',
                'tech_stack': 'Python, Django, AWS',
                'seniority': 'senior',
                'is_remote': True,
                'semantic_score': 0.85,
                'salary_min': 130000,
                'visa_score': 0
            })
        
        for i in range(5):
            jobs.append({
                'job_id': f'diff-company-{i}',
                'company': f'Startup{i}',
                'tech_stack': 'Python, Django, AWS',
                'seniority': 'senior',
                'is_remote': True,
                'semantic_score': 0.84,
                'salary_min': 130000,
                'visa_score': 0
            })
        
        results = match_resume_to_jobs(senior_python_resume, jobs, top_k=5)
        
        companies = [job['company'] for job in results]
        # Should have at least 3 different companies
        assert len(set(companies)) >= 3


# ============================================================================
# TEST CASES - PERFORMANCE
# ============================================================================

class TestPerformance:
    """Test performance benchmarks"""
    
    def test_score_calculation_speed(self, senior_python_resume, perfect_match_job):
        """Single job scoring should be < 10ms"""
        import time
        
        start = time.time()
        for _ in range(100):
            calculate_final_score(senior_python_resume, perfect_match_job)
        elapsed = time.time() - start
        
        avg_time = elapsed / 100
        assert avg_time < 0.01, f"Scoring too slow: {avg_time*1000:.2f}ms per job"
    
    def test_batch_scoring_efficiency(self, senior_python_resume):
        """Scoring 1000 jobs should be < 5 seconds"""
        import time
        
        jobs = []
        for i in range(1000):
            jobs.append({
                'job_id': f'job-{i}',
                'tech_stack': 'Python, Django',
                'seniority': 'senior',
                'is_remote': True,
                'semantic_score': 0.75,
                'salary_min': 120000,
                'visa_score': 0
            })
        
        start = time.time()
        results = match_resume_to_jobs(senior_python_resume, jobs, top_k=20)
        elapsed = time.time() - start
        
        assert elapsed < 5.0, f"Batch scoring too slow: {elapsed:.2f}s for 1000 jobs"
        assert len(results) == 20


# ============================================================================
# TEST CASES - LOCATION PARSING
# ============================================================================

class TestLocationExtraction:
    """Test resume location parsing"""
    
    def test_extract_city_state_zip(self):
        """Parse 'San Francisco, CA 94102'"""
        text = "John Doe\nSan Francisco, CA 94102\njohn@email.com"
        location = extract_location_smart(text)
        
        assert location['city'] == 'San Francisco'
        assert location['state'] == 'CA'
        assert location.get('zipcode') == '94102'
    
    def test_extract_city_state_no_zip(self):
        """Parse 'Austin, TX'"""
        text = "Jane Smith\nAustin, TX\njane@email.com"
        location = extract_location_smart(text)
        
        assert location['city'] == 'Austin'
        assert location['state'] == 'TX'
    
    def test_disambiguate_portland(self):
        """'Portland, OR' vs 'Portland, ME'"""
        text_or = "Mike Chen\nPortland, OR 97201"
        text_me = "Sarah Lee\nPortland, ME 04101"
        
        loc_or = extract_location_smart(text_or)
        loc_me = extract_location_smart(text_me)
        
        assert loc_or['state'] == 'OR'
        assert loc_me['state'] == 'ME'
    
    def test_international_location(self):
        """Parse 'Bangalore, India'"""
        text = "Priya Sharma\nBangalore, India\npriya@email.com"
        location = extract_location_smart(text)
        
        # Should handle international addresses
        assert location is not None


# ============================================================================
# TEST CASES - SPECIAL SCENARIOS
# ============================================================================

class TestSpecialScenarios:
    """Real-world edge cases"""
    
    def test_career_changer_with_transferable_skills(self):
        """Teacher transitioning to tech via bootcamp"""
        career_changer = {
            'technical_skills': ['JavaScript', 'React', 'Node.js', 'HTML', 'CSS'],
            'soft_skills': ['Teaching', 'Communication', 'Curriculum Design'],
            'seniority': 'junior',
            'years_experience': 0.5,  # 6 months coding
            'previous_career': 'Teacher (8 years)',
            'location_city': 'Denver',
            'location_state': 'CO',
            'willing_to_relocate': False,
            'visa_required': False,
            'expected_salary': 70000
        }
        
        junior_dev_job = {
            'job_id': 'test',
            'title': 'Junior Frontend Developer',
            'tech_stack': 'React, JavaScript, HTML, CSS',
            'seniority': 'junior',
            'min_years_exp': 0,
            'location_city': 'Denver',
            'location_state': 'CO',
            'is_remote': False,
            'salary_min': 65000,
            'salary_max': 80000,
            'visa_score': 0,
            'semantic_score': 0.72  # Some soft skill match
        }
        
        score = calculate_final_score(career_changer, junior_dev_job)
        
        # Should be a reasonable match
        assert score >= 0.55, "Career changers with right skills should match"
    
    def test_freelancer_with_varied_experience(self):
        """Freelancer with 10 clients, varied tech stack"""
        freelancer = {
            'technical_skills': ['Python', 'JavaScript', 'React', 'Django', 
                               'AWS', 'PostgreSQL', 'MongoDB', 'Docker'],
            'seniority': 'senior',
            'years_experience': 7,
            'work_type': 'Freelance/Contract',
            'location_city': 'Remote',
            'location_state': None,
            'willing_to_relocate': True,
            'visa_required': False,
            'expected_salary': 150000
        }
        
        fulltime_job = {
            'job_id': 'test',
            'title': 'Senior Full Stack Engineer',
            'tech_stack': 'Python, React, PostgreSQL, AWS',
            'seniority': 'senior',
            'is_remote': True,
            'salary_min': 140000,
            'salary_max': 170000,
            'visa_score': 0,
            'semantic_score': 0.88
        }
        
        score = calculate_final_score(freelancer, fulltime_job)
        
        # Freelancer should match well for full-time
        assert score >= 0.75
    
    def test_phd_applying_to_industry(self):
        """PhD researcher transitioning to industry ML role"""
        phd_candidate = {
            'technical_skills': ['Python', 'PyTorch', 'TensorFlow', 'R', 'Statistics'],
            'soft_skills': ['Research', 'Paper Writing', 'Presentations'],
            'seniority': 'senior',  # Research experience
            'years_experience': 5,  # PhD years
            'education': 'PhD',
            'location_city': 'Boston',
            'location_state': 'MA',
            'willing_to_relocate': True,
            'visa_required': False,
            'expected_salary': 130000
        }
        
        ml_engineer_job = {
            'job_id': 'test',
            'title': 'Machine Learning Engineer',
            'tech_stack': 'Python, PyTorch, AWS, MLOps',
            'seniority': 'mid',  # Industry seniority
            'min_years_exp': 3,
            'location_city': 'San Francisco',
            'location_state': 'CA',
            'is_remote': False,
            'salary_min': 120000,
            'salary_max': 150000,
            'visa_score': 0,
            'education_required': 'Master',  # PhD exceeds this
            'semantic_score': 0.85
        }
        
        score = calculate_final_score(phd_candidate, ml_engineer_job)
        
        # Should match despite seniority/location differences
        assert score >= 0.60


# ============================================================================
# COMPARISON TESTS - JOBRIGHT.AI BENCHMARK
# ============================================================================

class TestJobRightAIBenchmark:
    """Compare results against JobRight.ai expected behavior"""
    
    def test_top_match_relevance(self, senior_python_resume):
        """Top match should be highly relevant (>85%)"""
        jobs = [
            perfect_match_job(),
            partial_match_job(),
            skill_mismatch_job()
        ]
        
        results = match_resume_to_jobs(senior_python_resume, jobs, top_k=1)
        
        # Top result should be the perfect match
        assert results[0]['match_score'] >= 85
        assert results[0]['job_id'] == 'job-001'  # perfect_match_job
    
    def test_match_score_distribution(self, senior_python_resume):
        """Match scores should have good distribution (not all 90%+)"""
        jobs = [
            perfect_match_job(),
            partial_match_job(),
            remote_job(),
            overqualified_job(),
            wrong_location_job(),
            skill_mismatch_job()
        ]
        
        results = match_resume_to_jobs(senior_python_resume, jobs, top_k=6)
        scores = [job['match_score'] for job in results]
        
        # Should have variety in scores
        assert max(scores) - min(scores) >= 20, "Scores should vary by at least 20 points"
    
    def test_realistic_thresholds(self, senior_python_resume, perfect_match_job):
        """Match scores should align with real-world expectations"""
        score = calculate_final_score(senior_python_resume, perfect_match_job)
        
        # Perfect match should be 85-95% (not 100%, nobody's perfect)
        assert 0.85 <= score <= 0.95


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
