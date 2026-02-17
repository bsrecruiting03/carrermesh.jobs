from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time

# Metrics definitions
SCRAPER_JOBS_TOTAL = Counter(
    "scraper_jobs_total", 
    "Total number of jobs successfully fetched",
    ["source", "company"]
)

SCRAPER_ERRORS_TOTAL = Counter(
    "scraper_errors_total", 
    "Total number of scraping errors",
    ["source", "company", "error_type"]
)

SCRAPER_DURATION = Histogram(
    "scraper_duration_seconds", 
    "Seconds spent on a single scraping task",
    ["source", "company"],
    buckets=(1, 2, 5, 10, 30, 60, 120, 300)
)

QUEUE_DEPTH = Gauge(
    "scraper_queue_depth", 
    "Current number of tasks in the Redis queue",
    ["queue_name"]
)

def monitor_metrics_endpoint():
    """FastAPI endpoint to export Prometheus metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

class Monitor:
    @staticmethod
    def record_success(source: str, company: str, count: int, duration: float):
        SCRAPER_JOBS_TOTAL.labels(source=source, company=company).inc(count)
        SCRAPER_DURATION.labels(source=source, company=company).observe(duration)

    @staticmethod
    def record_error(source: str, company: str, error_type: str):
        SCRAPER_ERRORS_TOTAL.labels(source=source, company=company, error_type=error_type).inc()

    @staticmethod
    def set_queue_depth(queue_name: str, depth: int):
        QUEUE_DEPTH.labels(queue_name=queue_name).set(depth)
