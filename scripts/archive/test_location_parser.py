
from us_ats_jobs.resume.parser import ResumeParser

def test_locations():
    parser = ResumeParser()
    
    samples = [
        "Bangalore, India",
        "London, UK",
        "Berlin, Germany",
        "Toronto, ON, Canada",
        "New York, NY",
        "Mumbai, Maharashtra"
    ]
    
    print("Testing Location Extraction:\n")
    for text in samples:
        loc = parser.extract_location_smart(text)
        print(f"'{text}' -> {loc}")

if __name__ == "__main__":
    test_locations()
