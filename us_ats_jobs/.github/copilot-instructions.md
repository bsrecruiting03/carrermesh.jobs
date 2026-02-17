# AI Coding Guidelines for Job Board Scraper

## Architecture Overview
This project aggregates job listings from multiple Applicant Tracking Systems (ATS) and job search APIs. The core flow is:
1. Fetch raw job data from sources (Greenhouse, Lever, JSearch)
2. Normalize each job to a consistent schema
3. Deduplicate by job_id
4. Export to Excel

**Key Components:**
- `main.py`: Orchestrates fetching, normalization, and export
- `sources/*.py`: Platform-specific HTTP fetchers
- `normalizer.py`: Platform-specific data normalizers

## Data Flow & Schema
All jobs are normalized to this exact schema:
```python
{
    "job_id": f"{source}_{original_id}",  # e.g., "greenhouse_12345"
    "title": str,
    "company": str,
    "location": str,
    "job_description": str,
    "job_link": str,
    "source": str  # "greenhouse", "lever", or "jsearch"
}
```

## Adding New Sources
1. Create `sources/newsource.py` with `fetch_newsource_jobs()` function
2. Add `normalize_newsource()` in `normalizer.py`
3. Import both in `main.py`
4. Add source loop in main.py (follow Greenhouse/Lever pattern)
5. Add companies to appropriate list if ATS-based

## Development Workflow
- **Run scraper**: `python main.py`
- **Output**: `output/us_jobs_step_B.xlsx` (created automatically)
- **Dependencies**: `requests`, `pandas` (install via pip)
- **API Keys**: JSearch key is hardcoded in main.py (replace with env var for production)

## Code Patterns
- **HTTP requests**: Use `requests.get()` with `timeout=10-15` and `raise_for_status()`
- **Error handling**: Minimal - requests raise exceptions on HTTP errors
- **Deduplication**: `df.drop_duplicates(subset=["job_id"])` after collecting all jobs
- **Company lists**: Extend `GREENHOUSE_COMPANIES`/`LEVER_COMPANIES` arrays for new targets
- **Job ID generation**: Always prefix with source name to ensure uniqueness

## Key Files
- [main.py](main.py): Main orchestration and configuration
- [normalizer.py](normalizer.py): Data normalization functions
- [sources/](sources/): Platform-specific fetchers</content>
<parameter name="filePath">c:\Users\DELL\OneDrive\Desktop\job board\us_ats_jobs\.github\copilot-instructions.md