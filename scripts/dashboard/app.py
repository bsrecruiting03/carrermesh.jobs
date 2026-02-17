import os
import sys
import logging
from typing import List, Dict
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import psycopg2

# Add project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DB_URL = "postgresql://postgres:password@127.0.0.1:5433/job_board"

app = FastAPI(title="Job Board Operations Dashboard")

# Setup Templates
templates = Jinja2Templates(directory="scripts/dashboard/templates")

def get_db():
    conn = psycopg2.connect(DB_URL)
    return conn

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/stats/summary")
async def get_summary():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM career_endpoints WHERE active = TRUE")
        active_endpoints = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM jobs") # Use a counter cache in real prod
        total_jobs = cur.fetchone()[0]
        
        # New ATS found today? (Approx by created_at)
        cur.execute("SELECT COUNT(*) FROM career_endpoints WHERE created_at > CURRENT_DATE")
        new_endpoints_today = cur.fetchone()[0]
        
        # Jobs Ingested Today (Approx by raw_jobs fetched_at?)
        # Or raw_jobs.
        cur.execute("SELECT COUNT(*) FROM raw_jobs WHERE fetched_at > CURRENT_DATE")
        jobs_ingested_today = cur.fetchone()[0]
        
        return {
            "active_endpoints": active_endpoints,
            "total_jobs": total_jobs,
            "new_endpoints_today": new_endpoints_today,
            "jobs_ingested_today": jobs_ingested_today
        }
    finally:
        conn.close()

@app.get("/api/stats/ingestion_history")
async def get_ingestion_history():
    conn = get_db()
    cur = conn.cursor()
    try:
        # Group raw_jobs by hour (last 24h)
        cur.execute("""
            SELECT date_trunc('hour', fetched_at) as hour, COUNT(*) 
            FROM raw_jobs 
            WHERE fetched_at > NOW() - INTERVAL '24 hours'
            GROUP BY hour 
            ORDER BY hour ASC
        """)
        rows = cur.fetchall()
        
        labels = [r[0].strftime("%H:%M") for r in rows]
        data = [r[1] for r in rows]
        
        return {"labels": labels, "data": data}
    finally:
        conn.close()

@app.get("/api/stats/ats_distribution")
async def get_ats_distribution():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT ats_provider, COUNT(*) 
            FROM career_endpoints 
            GROUP BY ats_provider 
            ORDER BY COUNT(*) DESC 
            LIMIT 10
        """)
        rows = cur.fetchall()
        return [{"name": r[0], "value": r[1]} for r in rows]
    finally:
        conn.close()

@app.get("/api/stats/recent_discoveries")
async def get_recent_discoveries():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT ats_provider, ats_slug, canonical_url, created_at 
            FROM career_endpoints 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        rows = cur.fetchall()
        return [
            {
                "provider": r[0], 
                "slug": r[1], 
                "url": r[2], 
                "discovered": r[3].isoformat() if r[3] else "Unknown"
            } 
            for r in rows
        ]
    finally:
        conn.close()

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)
