# Job Board API - Prototype

## Overview
REST API for the job board platform built with FastAPI.

## Features
- ✅ Job search with advanced filtering
- ✅ Full-text search (title, company, description)
- ✅ Company management
- ✅ Filter options API
- ✅ Pagination and sorting
- ✅ CORS support
- ✅ OpenAPI documentation

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set environment variables:**
Create a `.env` file:
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/job_board
```

3. **Run the server:**
```bash
# Development mode (with auto-reload)
uvicorn main:app --reload --port 8000

# Or using Python directly
python main.py
```

## API Endpoints

### Jobs
- `GET /api/jobs` - Search and filter jobs
- `GET /api/jobs/{job_id}` - Get job details

### Companies
- `GET /api/companies` - List companies
- `GET /api/companies/{company_id}` - Get company details

### Filters
- `GET /api/filters` - Get available filter options

### Health
- `GET /api/health` - Health check

## Documentation

Once the server is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Example API Calls

### Search for Python jobs
```bash
curl "http://localhost:8000/api/jobs?q=python&limit=10"
```

### Filter remote jobs in San Francisco
```bash
curl "http://localhost:8000/api/jobs?location=San%20Francisco&remote=true"
```

### Filter by tech stack
```bash
curl "http://localhost:8000/api/jobs?tech_stack=Python,Django,PostgreSQL"
```

### Get job details
```bash
curl "http://localhost:8000/api/jobs/greenhouse_abc123"
```

### Get filter options
```bash
curl "http://localhost:8000/api/filters"
```

## Query Parameters

### `/api/jobs`
- `q` (string): Search query
- `location` (string): Location filter
- `remote` (boolean): Remote jobs only
- `department` (string): Department filter
- `tech_stack` (string): Comma-separated tech stack
- `min_salary` (int): Minimum salary
- `visa_sponsorship` (string): "yes", "no", "maybe"
- `posted_since` (string): "7d", "30d", etc.
- `sort` (string): "date_posted", "title", "company", "salary"
- `page` (int): Page number (default: 1)
- `limit` (int): Results per page (default: 20, max: 100)

## Architecture

```
api/
├── main.py          # FastAPI app and routes
├── models.py        # Pydantic models
├── database.py      # Database queries
├── config.py        # Configuration
└── requirements.txt # Dependencies
```

## Error Handling

The API returns standard HTTP status codes:
- `200` - Success
- `404` - Resource not found
- `422` - Validation error
- `500` - Internal server error

## CORS

CORS is enabled for:
- `http://localhost:3000`
- `http://localhost:3001`

Modify `config.py` to add more origins.

## Next Steps (Production)
- [ ] Add connection pooling (asyncpg)
- [ ] Implement retry logic
- [ ] Add circuit breakers
- [ ] Implement caching (Redis)
- [ ] Add rate limiting
- [ ] Full-text search indexes
- [ ] Performance optimization
