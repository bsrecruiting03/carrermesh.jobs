"""Pydantic models for API requests and responses."""
from typing import Optional, List, Dict
from datetime import datetime
from pydantic import BaseModel, Field


# ============= JOB MODELS =============

class JobListItem(BaseModel):
    """Job item in search results list."""
    job_id: str
    title: str
    company: str
    location: Optional[str] = None
    is_remote: bool = False
    work_mode: Optional[str] = None
    department: Optional[str] = None
    department_category: Optional[str] = None
    seniority: Optional[str] = None
    date_posted: Optional[datetime] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    visa_sponsorship: Optional[str] = None
    visa_confidence: Optional[float] = None
    job_link: Optional[str] = None
    source: Optional[str] = None
    tech_stack: Optional[List[str]] = None  # Parsed from enrichment
    job_summary: Optional[str] = None  # Short description for card insights
    experience_years: Optional[float] = None  # From enrichment
    
    # New Fields for Job Card
    normalized_location: Optional[str] = None
    logo_url: Optional[str] = None
    skills: Optional[List[str]] = None
    ingested_at: Optional[datetime] = None
    employment_type: Optional[str] = None

    class Config:
        from_attributes = True



class JobEnrichment(BaseModel):
    """Job enrichment/intelligence data."""
    tech_languages: Optional[str] = None
    tech_frameworks: Optional[str] = None
    tech_cloud: Optional[str] = None
    tech_data: Optional[str] = None
    tech_tools: Optional[str] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    experience_years: Optional[float] = None  # Unified experience
    education: Optional[str] = None
    education_level: Optional[str] = None
    seniority_tier: Optional[str] = None
    seniority_level: Optional[int] = None
    certifications: Optional[str] = None
    soft_skills: Optional[List[str]] = None
    clearance: Optional[str] = None
    natural_languages: Optional[str] = None
    
    class Config:
        from_attributes = True


class CompanyDetails(BaseModel):
    """Company information."""
    name: str
    domain: Optional[str] = None
    ats_provider: Optional[str] = None
    
    class Config:
        from_attributes = True


class JobDetail(BaseModel):
    """Full job details including description and enrichment."""
    job_id: str
    title: str
    company: str
    location: Optional[str] = None
    normalized_location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    job_description: Optional[str] = None
    job_summary: Optional[str] = None  # From enrichment
    job_link: Optional[str] = None
    source: Optional[str] = None
    date_posted: Optional[datetime] = None
    posted_bucket: Optional[str] = None
    is_remote: bool = False
    work_mode: Optional[str] = None
    seniority: Optional[str] = None
    department: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    visa_sponsorship: Optional[str] = None
    visa_confidence: Optional[float] = None
    enrichment: Optional[JobEnrichment] = None
    company_details: Optional[CompanyDetails] = None
    
    class Config:
        from_attributes = True


class JobSearchResponse(BaseModel):
    """Paginated job search results."""
    total: int
    page: int
    limit: int
    pages: int
    jobs: List[JobListItem]


# ============= COMPANY MODELS =============

class CompanyListItem(BaseModel):
    """Company item in list."""
    id: int
    name: str
    domain: Optional[str] = None
    ats_provider: Optional[str] = None
    active_jobs_count: int = 0
    last_scraped_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CompanyDetail(BaseModel):
    """Full company details."""
    id: int
    name: str
    domain: Optional[str] = None
    career_page_url: Optional[str] = None
    ats_provider: Optional[str] = None
    active: bool = True
    job_count: int = 0
    recent_jobs: List[JobListItem] = []
    
    class Config:
        from_attributes = True


class CompanyListResponse(BaseModel):
    """Paginated company list."""
    total: int
    page: int
    limit: int
    companies: List[CompanyListItem]


# ============= FILTER MODELS =============

class FiltersResponse(BaseModel):
    """Available filter options."""
    locations: List[str]
    departments: Dict[str, List[str]]
    tech_languages: List[str]
    tech_frameworks: List[str]
    ats_providers: List[str]
    seniority_levels: List[str]
    work_modes: List[str]


# ============= HEALTH CHECK =============

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    db_connected: bool
    timestamp: datetime
