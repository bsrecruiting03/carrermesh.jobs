import requests
import re

def fetch_lever_jobs(company, endpoint_url=None):
    slug = company
    
    if endpoint_url:
        try:
            clean = endpoint_url.replace("https://", "").replace("http://", "")
            parts = clean.split("/")
            if len(parts) > 1 and parts[1]:
                slug = parts[1]
        except: pass
        
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except:
        return []

