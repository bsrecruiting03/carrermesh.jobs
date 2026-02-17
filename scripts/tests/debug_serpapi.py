"""Quick debug test for SerpAPI key"""
import requests

API_KEY = "LW1KgjX8vU9KsvhzmLpRow98"

# Test 1: Basic Google search (uses 1 credit)
print("Testing SerpAPI with basic Google search...")
params = {
    "engine": "google",
    "q": "software engineer jobs at google",
    "api_key": API_KEY,
    "num": 3
}

try:
    resp = requests.get("https://serpapi.com/search", params=params, timeout=30)
    print(f"Status: {resp.status_code}")
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"Success! Keys: {list(data.keys())}")
        if "organic_results" in data:
            print(f"Found {len(data['organic_results'])} organic results")
    else:
        print(f"Error: {resp.text[:300]}")
        
except Exception as e:
    print(f"Exception: {e}")
