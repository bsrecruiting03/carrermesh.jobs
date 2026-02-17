
import json
import os
import re
from typing import Dict, List, Tuple, Optional

class DepartmentClassifier:
    def __init__(self, taxonomy_path: Optional[str] = None):
        if not taxonomy_path:
            base_path = os.path.dirname(os.path.abspath(__file__))
            taxonomy_path = os.path.join(base_path, "department_taxonomy.json")
            
        self.taxonomy = self._load_taxonomy(taxonomy_path)
        # Create a reverse mapping: keyword -> (Category, SubCategory)
        # We perform pre-compilation of keywords to regex for performance/accuracy
        self.keyword_map = self._build_keyword_map()

    def _load_taxonomy(self, path: str) -> Dict:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading taxonomy: {e}")
            return {}

    def _build_keyword_map(self) -> List[Tuple[str, str, str]]:
        """
        Builds a prioritized list of (Category, SubCategory, Keyword).
        Longer keywords match first to capture specific roles (e.g. "Software Engineer")
        before generic ones (e.g. "Engineer").
        """
        mapping = []
        for category, subcats in self.taxonomy.items():
            for subcat, keywords in subcats.items():
                for keyword in keywords:
                    mapping.append((category, subcat, keyword.lower()))
        
        # Sort by keyword length descending (Longest Match First)
        mapping.sort(key=lambda x: len(x[2]), reverse=True)
        return mapping

    def classify(self, title: str) -> Tuple[str, str]:
        """
        Classifies a job title into (Category, SubCategory).
        Returns ("Uncategorized", "Uncategorized") if no match found.
        """
        if not title:
            return "Other", "Uncategorized"
            
        title_lower = title.lower()
        
        # 1. Direct Keyword Match
        for category, subcat, keyword in self.keyword_map:
            # Use word boundary check to avoid partial matches (e.g. avoiding "Analyst" inside "Psychoanalyst" if we didn't want it)
            # Actually for departments, "Software Engineer" contains "Engineer".
            # Since we sorted by length, "Software Engineer" pattern check comes before "Engineer".
            
            # Simple substring often works, but word boundary is safer.
            # Escaping keyword to handle C++, .NET etc.
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, title_lower):
                return category, subcat
                
        return "Other", "Uncategorized"

if __name__ == "__main__":
    # Test Suite
    clf = DepartmentClassifier()
    
    test_titles = [
        "Senior Software Engineer",
        "Registered Nurse - ICU",
        "VP of Sales",
        "Part-time Warehouse Worker",
        "Clinical Psychologist",
        "Hiring a Python Developer",
        "Chief Financial Officer",
        "Forklift Driver",
        "Unknown Role 123"
    ]
    
    print("--- Classification Tests ---")
    for t in test_titles:
        cat, sub = clf.classify(t)
        print(f"'{t}' -> {cat} / {sub}")
