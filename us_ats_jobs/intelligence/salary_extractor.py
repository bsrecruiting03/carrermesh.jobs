import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger("SalaryExtractor")

class SalaryExtractor:
    """
    Advanced Salary Extraction with support for:
    - Multi-currency ($, €, £, USD, etc.)
    - Varied pay periods (hourly, monthly, yearly)
    - Range detection ($100k - $120k)
    - Unit scaling (hourly -> annual)
    """
    
    # regex to catch currency symbols/codes
    CURRENCY_SYMBOLS = r"[\$€£]|(?:USD|EUR|GBP|CAD|AUD)\s?"
    
    # regex for numbers like 100,000 or 100k or 1200 or 10.5
    # Added M/B to noise detection
    NUM_PATTERN = r"(?:\d{1,3}(?:[,.\s]\d{3})+|\d{1,6})(?:[kKmMbB]\b)?"
    
    # Combined Range Regex
    RANGE_REGEX = re.compile(
        rf"(?:(?P<pref>{CURRENCY_SYMBOLS}))?\s?"
        rf"(?P<low>{NUM_PATTERN})"
        rf"(?:\s*(?:-|to|and|until)\s*(?:{CURRENCY_SYMBOLS})?\s*(?P<high>{NUM_PATTERN}))?"
        rf"(?:\s*(?P<suff>{CURRENCY_SYMBOLS}))?"
        rf"(?:\s*(?:/|per|p/|a|an)\s*)?"
        rf"(?P<unit>(?:year|yr|annual|annum|month|mo|week|wk|day|hour|hr|h))?\b",
        re.IGNORECASE
    )

    def _clean_number(self, s: str) -> Optional[float]:
        if not s: return None
        s_orig = s.lower().strip()
        
        # If it ends with M or B (Million/Billion), it's almost certainly not a salary but a market size
        if s_orig.endswith('b') or s_orig.endswith('m'):
            # We filter it out by returning None
            return None

        factor = 1.0
        if s_orig.endswith('k'):
            factor = 1000.0
            s_orig = s_orig[:-1]
        
        # Remove common separators
        s_clean = s_orig.replace(",", "").replace(" ", "")
        
        # Handle EU format dot as thousands separator (e.g. 100.000) 
        if "." in s_clean:
            parts = s_clean.split(".")
            if len(parts) == 2 and len(parts[1]) == 3:
                s_clean = s_clean.replace(".", "")
        
        try:
            return float(s_clean) * factor
        except:
            return None

    def _get_multiplier(self, unit: str) -> float:
        """Scales pay unit to Annual. Stricter matching to avoid 'month' -> 'h' collision."""
        if not unit: return 1.0
        u = unit.lower().strip()
        # Use exact or prefix matching for clarity
        if u in ["h", "hr", "hour", "hourly"]: return 2000.0
        if u in ["day", "daily"]: return 260.0
        if u in ["wk", "week", "weekly"]: return 52.0
        if u in ["mo", "month", "monthly"]: return 12.0
        if u in ["yr", "year", "annual", "annum"]: return 1.0
        return 1.0

    def extract(self, text: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
        if not text: return None, None, None
        
        # Normalize text
        t = text.replace("\u2013", "-").replace("\u2014", "-")
        
        matches = list(self.RANGE_REGEX.finditer(t))
        if not matches: return None, None, None
        
        results = []
        # Keywords that usually indicate market data, not salary
        BLACKLIST_KEYWORDS = ["industry", "market", "revenue", "funding", "raised", "capital", "valuation", "budget for", "worth"]
        
        for m in matches:
            # Check context (±50 chars) for blacklisted keywords
            start_ctx = max(0, m.start() - 50)
            end_ctx = min(len(t), m.end() + 50)
            context = t[start_ctx:end_ctx].lower()
            
            if any(kw in context for kw in BLACKLIST_KEYWORDS):
                # Extra check: if it has a salary indicator like "salary" or "pay" or "rate", we might keep it
                if not any(kw in context for kw in ["salary", "pay", "rate", "compensation", "per year"]):
                    continue

            gd = m.groupdict()
            low = self._clean_number(gd.get("low"))
            high = self._clean_number(gd.get("high")) if gd.get("high") else low
            unit = gd.get("unit")
            
            if low is None: continue
            
            # Sanity Check for years/dates (ignore if no currency or unit and is 1990-2035)
            if not gd.get("pref") and not gd.get("suff") and not unit:
                if 1990 <= low <= 2035: continue
            
            mult = self._get_multiplier(unit)
            low_scaled = low * mult
            high_scaled = high * mult
            
            # Final sanity thresholds for annual salary
            if high_scaled < 15000 and not unit: continue 
            if high_scaled < 1000: continue 
            if low_scaled > 10000000: continue 

            # Currency
            currency = "USD"
            curr_str = (gd.get("pref") or gd.get("suff") or "").upper()
            if "€" in curr_str or "EUR" in curr_str: currency = "EUR"
            elif "£" in curr_str or "GBP" in curr_str: currency = "GBP"
            
            results.append({
                "low": low_scaled, 
                "high": high_scaled, 
                "currency": currency,
                "start": m.start(),
                "end": m.end()
            })

        if not results: return None, None, None
        
        # Merge logic: if we have two matches very close to each other (e.g. "$60/hr to $90/hr")
        # we should combine them.
        final_results = []
        if len(results) >= 2:
            results.sort(key=lambda x: x['start'])
            i = 0
            while i < len(results):
                curr = results[i]
                if i + 1 < len(results):
                    next_res = results[i+1]
                    # If they are within 10 chars of each other
                    if next_res['start'] - curr['end'] < 10:
                        # Merge them
                        merged = {
                            "low": min(curr['low'], next_res['low']),
                            "high": max(curr['high'], next_res['high']),
                            "currency": curr['currency'],
                            "start": curr['start'],
                            "end": next_res['end']
                        }
                        final_results.append(merged)
                        i += 2
                        continue
                final_results.append(curr)
                i += 1
        else:
            final_results = results

        # Sort by high value and return largest range found
        final_results.sort(key=lambda x: x['high'], reverse=True)
        best = final_results[0]
        return best['low'], best['high'], best['currency']

# Singleton
_extractor = SalaryExtractor()
def extract_salary(text: str):
    return _extractor.extract(text)

if __name__ == "__main__":
    # Test cases
    te = SalaryExtractor()
    tests = [
        "$100k - $150k",
        "120,000 - 140,000 USD",
        "Salary: 50.000€ per year",
        "Rate is $60/hr to $90 per hour",
        "Up to 200k USD",
        "1200 - 1500 per month",
        "In 2024, our budget is 2025..." # false positive check
    ]
    for t in tests:
        print(f"'{t}' -> {te.extract(t)}")
