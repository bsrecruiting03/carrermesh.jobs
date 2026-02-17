"""Configuration for the Job Board API."""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """API Settings loaded from environment variables."""
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:password@127.0.0.1:5433/job_board").replace("localhost", "127.0.0.1")
    
    # API Settings
    api_title: str = "Job Board API"
    api_version: str = "1.0.0"
    api_description: str = "REST API for job board platform"
    
    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100
    
    # CORS
    cors_origins: list = ["http://localhost:3000", "http://localhost:3001"]


# Global settings instance
settings = Settings()
