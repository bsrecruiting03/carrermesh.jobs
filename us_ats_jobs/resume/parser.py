import fitz  # PyMuPDF
import docx
import re
import logging
from typing import Dict, Optional, List, Tuple
from fastapi import UploadFile

logger = logging.getLogger("ResumeParser")

class ResumeParser:
    def __init__(self):
        pass

    def parse(self, file_content: bytes, filename: str) -> Dict:
        """
        Main entry point. Detects file type and extracts text + metadata.
        """
        filename = filename.lower()
        text = ""
        
        try:
            if filename.endswith(".pdf"):
                text = self._parse_pdf(file_content)
            elif filename.endswith(".docx"):
                text = self._parse_docx(file_content)
            else:
                raise ValueError("Unsupported file format. Please upload PDF or DOCX.")

            # Clean Text
            text = self._clean_text(text)
            
            # Extract Metadata (Basic Regex)
            metadata = self._extract_metadata(text)
            
            return {
                "text": text,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to parse resume {filename}: {e}")
            raise e

    def _parse_pdf(self, file_content: bytes) -> str:
        """
        Extracts text from PDF using PyMuPDF (fitz).
        Sorts blocks to handle columns correctly.
        """
        doc = fitz.open(stream=file_content, filetype="pdf")
        full_text = []

        for page in doc:
            # get_text("blocks") returns: (x0, y0, x1, y1, "text", block_no, block_type)
            blocks = page.get_text("blocks")
            
            # Sort blocks: Top-to-Bottom, then Left-to-Right
            # key: (y0, x0)
            blocks.sort(key=lambda b: (b[1], b[0]))
            
            for b in blocks:
                # b[4] is the text content
                if b[6] == 0: # 0 = text, 1 = image
                    full_text.append(b[4].strip())
                    
        return "\n".join(full_text)

    def _parse_docx(self, file_content: bytes) -> str:
        """
        Extracts text from DOCX using python-docx.
        """
        from io import BytesIO
        doc = docx.Document(BytesIO(file_content))
        full_text = []
        for para in doc.paragraphs:
            if para.text.strip():
                full_text.append(para.text.strip())
        return "\n".join(full_text)

    def _clean_text(self, text: str) -> str:
        # Remove weird characters
        text = text.encode("ascii", "ignore").decode()
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _extract_metadata(self, text: str) -> Dict:
        """
        Extracts Email, Phone, and (Attempted) Location.
        """
        meta = {
            "email": None,
            "phone": None,
            "years_experience": 0.0,
            "location": self.extract_location_smart(text)
        }
        
        # Email Regex
        email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)
        if email_match:
            meta["email"] = email_match.group(0)

        # Phone Regex (Generic)
        phone_match = re.search(r'(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', text)
        if phone_match:
            meta["phone"] = phone_match.group(0)

        # Years of Experience Heuristic
        # Look for "5+ years", "10 years of experience"
        exp_matches = re.findall(r'(\d+)\+?\s*(?:year|yr)s?', text.lower())
        if exp_matches:
            # Take the MAX number found (assuming it's the total)
            # Filter out crazy numbers (like 2023 years)
            valid_years = [int(y) for y in exp_matches if int(y) < 40]
        if valid_years:
                meta["years_experience"] = float(max(valid_years))

        # Current Role Extraction
        meta["current_role"] = self._extract_role(text)

        return meta

    def _extract_role(self, text: str) -> Optional[str]:
        """
        Heuristic to find the candidate's current or target role.
        Scans the top of the resume (header) for common job titles.
        """
        # Common tech titles (can be expanded)
        # We look for these primarily in the first 500 characters (Header)
        header_text = text[:800]
        
        # Regex for common roles
        # Matches: "Senior Software Engineer", "Full Stack Developer", "Data Scientist", etc.
        # (Senior|Lead|...)?\s?(\w+\s)?(Engineer|Developer|Scientist|Architect|Manager|Designer)
        
        role_patterns = [
            r"(?i)\b(Senior|Junior|Lead|Staff|Principal|Chief|Head of)?[ \t]*(\w+[ \t]+){0,2}(Software|Data|Systems|DevOps|Site Reliability|QA|Frontend|Backend|Full Stack|Product|Project|Machine Learning|AI)[ \t]+(Engineer|Developer|Scientist|Architect|Manager|Designer|Analyst|Consultant)\b",
            r"(?i)\b(CTO|CEO|VP of Engineering|Director of Engineering|Engineering Manager)\b"
        ]
        
        for pattern in role_patterns:
            match = re.search(pattern, header_text)
            if match:
                # Clean up the found title
                return match.group(0).strip().title()
                
        return None

    def extract_location_smart(self, text: str) -> Dict:
        """
        Smart location extraction.
        Prioritizes explicit Country detection, then US Zipcodes, then City/State regex.
        """
        from uszipcode import SearchEngine
        
        # Limit scan to header
        scan_text = text[:2000]
        
        # 1. explicit Country Detection
        # Add more as needed. These are common in tech.
        countries = {
            "India": "India", "Bharat": "India",
            "United Kingdom": "United Kingdom", "UK": "United Kingdom", "London": "United Kingdom",
            "Canada": "Canada",
            "Germany": "Germany", "Deutschland": "Germany", "Berlin": "Germany",
            "France": "France", "Paris": "France",
            "Australia": "Australia",
            "Singapore": "Singapore",
            "United States": "United States", "USA": "United States", "US": "United States"
        }
        
        # Check for "City, Country" pattern first? or just presense of Country?
        # Let's scan for the country name appearing in the text (usually address line)
        
        found_country = None
        # Naive scan - check if country matches a line or is part of a location string
        # To avoid False Positives (e.g. "I worked with India team"), strict check on lines might be better.
        # But for now, let's look for "City, Country" or just Country at end of line.
        
        # Reverse sort by length to match "United Kingdom" before "United" (if that was a key)
        for name, code in sorted(countries.items(), key=lambda x: len(x[0]), reverse=True):
             # Regex: Word boundary + Name + Word boundary/End of line
             if re.search(r'\b' + re.escape(name) + r'\b', scan_text, re.IGNORECASE):
                 found_country = code
                 break
                 
        # 2. Check US Zipcode (Strong Signal for US)
        # Matches 5 digit zip, maybe preceded by state code
        zip_match = re.search(r'\b(\d{5})\b', scan_text)
        if zip_match:
            zipcode = zip_match.group(1)
            search = SearchEngine()
            result = search.by_zipcode(zipcode)
            if result:
                 return {
                    "city": result.major_city,
                    "state": result.state,
                    "country": "United States",
                    "zipcode": zipcode,
                    "confidence": 0.95
                }

        # 3. Regex for "City, State" (US style mostly, but also "Mumbai, Maharashtra")
        pattern = r'([A-Z][a-zA-Z\s]+),\s*([A-Z]{2}|[A-Z][a-z]+)'
        match = re.search(pattern, scan_text)
        
        if match:
            city = match.group(1).strip()
            state_or_country = match.group(2).strip()
            
            # If we already found a country (e.g. "Bangalore, India"), use it.
            if found_country and found_country != "United States":
                 return {
                    "city": city,
                    "state": state_or_country if state_or_country != found_country else None,
                    "country": found_country,
                    "confidence": 0.9
                }
            
            # Check if city is a known major city to infer country
            inferred_country = found_country
            if not inferred_country:
                # Use the major_cities dict defined below (need to move it up or duplicate)
                # Let's define a helper or just check a few key ones here for now to fix Mumbai
                # Better: Move major_cities definition to class level or top of method
                pass 

        # 4. Fallback: Major Cities Dict (Extended)
        major_cities = {
            'San Francisco': 'United States', 'New York': 'United States', 
            'London': 'United Kingdom', 'Bangalore': 'India', 'Bengaluru': 'India',
            'Mumbai': 'India', 'Delhi': 'India', 'Berlin': 'Germany',
            'Toronto': 'Canada', 'Sydney': 'Australia', 'Paris': 'France'
        }

        if match:
             # Re-evaluate match logic with major_cities available
             if not inferred_country and city in major_cities:
                 inferred_country = major_cities[city]

             # If state looks like 2-letter US state code
             if len(state_or_country) == 2 and state_or_country.isupper():
                 return {
                    "city": city,
                    "state": state_or_country,
                    "country": "United States",
                    "confidence": 0.85
                }
                
             # Otherwise
             if len(state_or_country) > 2:
                 return {
                    "city": city,
                    "state": state_or_country,
                    "country": inferred_country, 
                    "confidence": 0.7 if inferred_country else 0.6
                }
        
        for city, ctry in major_cities.items():
            if city in scan_text:
                return {
                    "city": city,
                    "state": None,
                    "country": ctry,
                    "confidence": 0.7
                }
        
        return {
            "city": None, 
            "state": None, 
            "country": found_country, # Return found country even if no city
            "confidence": 0.5 if found_country else 0
        }
