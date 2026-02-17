"""FastAPI main application - Job Board API Prototype."""
from fastapi import FastAPI, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from datetime import datetime
import logging

from .config import settings
from .models import (
    JobSearchResponse, JobDetail, JobListItem,
    CompanyListResponse, CompanyListItem, CompanyDetail,
    FiltersResponse, HealthResponse
)
from . import database as db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from .monitoring import monitor_metrics_endpoint

@app.get("/metrics", tags=["Health"])
async def metrics():
    """Prometheus metrics endpoint."""
    return monitor_metrics_endpoint()

@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    db_connected = db.test_connection()
    
    return HealthResponse(
        status="healthy" if db_connected else "unhealthy",
        db_connected=db_connected,
        timestamp=datetime.now()
    )


# ============= JOB ENDPOINTS =============

@app.get("/api/jobs", response_model=JobSearchResponse, tags=["Jobs"])
async def search_jobs(
    q: Optional[str] = Query(None, description="Search query (title, company, description)"),
    location: Optional[str] = Query(None, description="Filter by location"),
    remote: Optional[bool] = Query(None, description="Remote jobs only"),
    department: Optional[str] = Query(None, description="Filter by department"),
    tech_stack: Optional[str] = Query(None, description="Comma-separated tech stack (e.g., 'Python,React')"),
    min_salary: Optional[int] = Query(None, description="Minimum salary filter"),
    max_salary: Optional[int] = Query(None, description="Maximum salary filter"),
    visa_sponsorship: Optional[str] = Query(None, description="Visa sponsorship: 'yes', 'no', 'maybe'"),
    remote_policy: Optional[str] = Query(None, description="Remote policy: 'remote', 'hybrid', 'onsite'"),
    seniority: Optional[str] = Query(None, description="Seniority level: 'junior', 'mid', 'senior', 'lead', 'principal'"),
    posted_since: Optional[str] = Query(None, description="Posted since (e.g., '7d', '30d')"),
    sort: str = Query("date_posted", description="Sort by: date_posted, title, company, salary"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page (max 100)")
):
    """
    Search and filter jobs.
    
    **Query Parameters:**
    - `q`: Search in title, company, or description
    - `location`: Filter by location (partial match)
    - `remote`: Filter for remote jobs (true/false)
    - `department`: Filter by department
    - `tech_stack`: Filter by tech stack (comma-separated, e.g., "Python,Django")
    - `min_salary`: Minimum salary threshold
    - `max_salary`: Maximum salary threshold
    - `visa_sponsorship`: Filter by visa sponsorship status
    - `remote_policy`: Filter by work mode ('remote', 'hybrid', 'onsite')
    - `seniority`: Filter by seniority level ('junior', 'mid', 'senior', 'lead', 'principal')
    - `posted_since`: Filter by recency (e.g., "7d" for last 7 days)
    - `sort`: Sort order (date_posted, title, company, salary)
    - `page`: Page number (starts at 1)
    - `limit`: Results per page (1-100)
    """
    try:
        # Try Meilisearch First
        from .services.search_service import search_service
        
        jobs, total = search_service.search_jobs(
            query=q,
            location=location,
            remote=remote,
            department=department,
            tech_stack=tech_stack,
            min_salary=min_salary,
            max_salary=max_salary,
            visa_sponsorship=visa_sponsorship,
            remote_policy=remote_policy,
            seniority=seniority,
            posted_since=posted_since,
            sort=sort,
            page=page,
            limit=limit
        )
        
        pages = (total + limit - 1) // limit  # Ceiling division
        
        return JobSearchResponse(
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            jobs=[JobListItem(**job) for job in jobs]
        )
    
    except Exception as e:
        logger.error(f"Error searching jobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/jobs/{job_id}", response_model=JobDetail, tags=["Jobs"])
async def get_job(job_id: str):
    """
    Get full job details by job ID.
    
    **Path Parameters:**
    - `job_id`: Unique job identifier
    """
    try:
        job = db.get_job_by_id(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        
        return JobDetail(**job)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job {job_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============= COMPANY ENDPOINTS =============

@app.get("/api/companies", response_model=CompanyListResponse, tags=["Companies"])
async def list_companies(
    ats_provider: Optional[str] = Query(None, description="Filter by ATS provider"),
    active: bool = Query(True, description="Active companies only"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page")
):
    """
    List companies with optional filters.
    
    **Query Parameters:**
    - `ats_provider`: Filter by ATS provider (e.g., "greenhouse", "lever")
    - `active`: Show only active companies (default: true)
    - `page`: Page number
    - `limit`: Results per page
    """
    try:
        companies, total = db.get_companies(
            ats_provider=ats_provider,
            active=active,
            page=page,
            limit=limit
        )
        
        return CompanyListResponse(
            total=total,
            page=page,
            limit=limit,
            companies=[CompanyListItem(**c) for c in companies]
        )
    
    except Exception as e:
        logger.error(f"Error listing companies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/companies/{company_id}", response_model=CompanyDetail, tags=["Companies"])
async def get_company(company_id: int):
    """
    Get company details by ID.
    
    **Path Parameters:**
    - `company_id`: Unique company identifier
    """
    try:
        company = db.get_company_by_id(company_id)
        
        if not company:
            raise HTTPException(status_code=404, detail=f"Company not found: {company_id}")
        
        return CompanyDetail(**company)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching company {company_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============= FILTER ENDPOINTS =============

@app.get("/api/filters", response_model=FiltersResponse, tags=["Filters"])
async def get_filters():
    """
    Get all available filter options.
    
    Returns distinct values for:
    - Locations
    - Departments
    - Tech languages
    - Tech frameworks
    - ATS providers
    - Seniority levels
    - Work modes
    """
    try:
        filters = db.get_filter_options()
        return FiltersResponse(**filters)
    
    except Exception as e:
        logger.error(f"Error fetching filters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/locations/suggest", tags=["Filters"])
async def suggest_locations(
    q: str = Query(..., min_length=2, description="Location prefix to search for"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Get location suggestions based on user input.
    Returns locations ordered by job count.
    """
    try:
        suggestions = db.get_location_suggestions(prefix=q, limit=limit)
        return {"results": suggestions}
    
    except Exception as e:
        logger.error(f"Error fetching location suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/jobs/suggest", tags=["Filters"])
async def suggest_jobs(
    q: str = Query(..., min_length=2, description="Job title or company prefix"),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Get job suggestions (titles, companies) based on user input.
    Returns list of mixed type results.
    """
    try:
        suggestions = db.get_job_suggestions(prefix=q, limit=limit)
        return {"results": suggestions}
    
    except Exception as e:
        logger.error(f"Error fetching job suggestions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============= RESUME MATCHING =============

@app.post("/api/match-resume", tags=["Resume"])
async def match_resume_endpoint(
    file: UploadFile,
    limit: int = Query(20, ge=1, le=50)
):
    """
    Upload a resume (PDF/DOCX) and get matched jobs.
    """
    from .services.resume_service import resume_service
    try:
        return await resume_service.match_resume(file, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error matching resume: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============= ROOT =============

@app.get("/", tags=["Root"])
async def root():
    """API root endpoint."""
    return {
        "message": "Job Board API",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
