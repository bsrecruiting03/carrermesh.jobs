

import os
import requests
import json
import csv
from pathlib import Path

API_URL = "http://localhost:8000/api/match-resume"
RESUME_DIR = "test_resumes"
OUTPUT_CSV = "resume_match_results.csv"

def test_resume(file_path):
    print(f"\n📄 Processing: {file_path.name}...")
    result = {
        "Resume": file_path.name,
        "Status": "Failed",
        "Top Role": "N/A",
        "Company": "N/A",
        "Total Score": 0.0,
        "Technical": 0.0,
        "Semantic": 0.0,
        "Seniority": 0.0,
        "Location": 0.0,
        "Salary": 0.0,
        "Visa": 0.0
    }
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/pdf" if file_path.suffix == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
            response = requests.post(API_URL, files=files)
            
        if response.status_code == 200:
            data = response.json()
            matches = data.get("matches", [])
            if matches:
                top = matches[0]
                job = top["job"]
                score = top["score"]
                bd = score["breakdown"]
                
                print(f"✅ Match Found: {score['total_score']}%")
                print(f"   Role: {job.get('title')} @ {job.get('company')}")
                
                result.update({
                    "Status": "Success",
                    "Top Role": job.get('title'),
                    "Company": job.get('company'),
                    "Total Score": score['total_score'],
                    "Technical": bd.get('technical', 0),
                    "Semantic": bd.get('semantic', 0),
                    "Seniority": bd.get('seniority', 0),
                    "Location": bd.get('location', 0),
                    "Salary": bd.get('salary', 0),
                    "Visa": bd.get('visa', 0)
                })
            else:
                print("⚠️ No matches found.")
                result["Status"] = "No Matches"
        else:
            print(f"❌ API Error: {response.status_code} - {response.text}")
            result["Status"] = f"API Error {response.status_code}"
            
    except Exception as e:
        print(f"❌ Failed: {e}")
        result["Status"] = str(e)
        
    return result

def main():
    folder = Path(RESUME_DIR)
    if not folder.exists():
        print(f"❌ Directory '{RESUME_DIR}' not found.")
        return

    files = list(folder.glob("*.pdf")) + list(folder.glob("*.docx"))
    
    if not files:
        print(f"⚠️ No PDF or DOCX files found in '{RESUME_DIR}'.")
        return
        
    print(f"🔍 Found {len(files)} resumes. Starting batch test...")
    
    results = []
    for file_path in files:
        results.append(test_resume(file_path))
        
    # Save to CSV
    keys = results[0].keys()
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(results)
        
    print(f"\n📊 Results saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()

