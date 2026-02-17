"""
Frequency Analysis Script for MIND Ontology Import
===================================================

This script analyzes existing job descriptions to determine which skills
from the MIND ontology actually appear in your job corpus. This prevents
importing thousands of niche skills that would never match.

Usage:
    python scripts/analyze_skill_frequency.py --output data/skill_frequency.json

Output:
    JSON file with skill frequencies for filtering MIND import
"""

import json
import psycopg2
import re
from collections import Counter
from pathlib import Path
import argparse
from typing import Dict, List, Tuple

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5433,
    "database": "job_board",
    "user": "postgres",
    "password": "postgres"
}

# MIND ontology files to analyze
MIND_FILES = [
    "MIND-tech-ontology-main/__aggregated_skills.json",
    # Or individual files:
    # "MIND-tech-ontology-main/skills/programming_languages.json",
    # "MIND-tech-ontology-main/skills/frameworks_frontend.json",
    # etc.
]


class SkillFrequencyAnalyzer:
    """Analyzes skill frequency in job descriptions"""
    
    def __init__(self, db_config: dict):
        self.conn = psycopg2.connect(**db_config)
        self.skill_counts = Counter()
        self.total_jobs = 0
        
    def load_mind_ontology(self, file_path: str) -> List[dict]:
        """Load MIND ontology skills from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both array and object formats
        if isinstance(data, list):
            return data
        else:
            # If it's an object with skills key
            return data.get('skills', [])
    
    def get_all_job_descriptions(self) -> List[Tuple[str, str]]:
        """Fetch all job descriptions and titles from database"""
        cur = self.conn.cursor()
        
        query = """
            SELECT job_id, title, job_description
            FROM jobs
            WHERE job_description IS NOT NULL
            ORDER BY ingested_at DESC
        """
        
        cur.execute(query)
        results = cur.fetchall()
        cur.close()
        
        self.total_jobs = len(results)
        print(f"Loaded {self.total_jobs} job descriptions")
        
        return [(job_id, f"{title} {description}") 
                for job_id, title, description in results]
    
    def create_skill_patterns(self, mind_skills: List[dict]) -> Dict[str, re.Pattern]:
        """Create regex patterns for all skills and synonyms"""
        patterns = {}
        
        for skill in mind_skills:
            canonical_name = skill.get('name', '')
            synonyms = skill.get('synonyms', [])
            
            if not canonical_name:
                continue
            
            # Combine canonical name and synonyms
            all_terms = [canonical_name] + synonyms
            
            # Create patterns with word boundaries
            for term in all_terms:
                if len(term) < 2:  # Skip very short terms
                    continue
                    
                # Escape special regex characters
                term_escaped = re.escape(term)
                
                # Create pattern with word boundaries
                # Use case-insensitive matching
                pattern = re.compile(
                    rf'\b{term_escaped}\b',
                    re.IGNORECASE
                )
                
                patterns[term.lower()] = {
                    'pattern': pattern,
                    'canonical': canonical_name
                }
        
        print(f"Created {len(patterns)} search patterns")
        return patterns
    
    def analyze_frequencies(self, jobs: List[Tuple[str, str]], 
                          patterns: Dict[str, dict]) -> Counter:
        """Analyze how often each skill appears in job descriptions"""
        skill_canonical_counts = Counter()
        
        # Track which skills appear in which jobs (for exact counting)
        job_skills = {}  # job_id -> set of canonical skill names
        
        for job_id, text in jobs:
            if job_id not in job_skills:
                job_skills[job_id] = set()
            
            text_lower = text.lower()
            
            # Search for each pattern
            for term, info in patterns.items():
                if info['pattern'].search(text):
                    canonical = info['canonical']
                    job_skills[job_id].add(canonical)
        
        # Count unique job appearances per skill
        for job_id, skills in job_skills.items():
            for skill in skills:
                skill_canonical_counts[skill] += 1
        
        return skill_canonical_counts
    
    def generate_report(self, skill_counts: Counter, 
                       mind_skills: List[dict]) -> dict:
        """Generate comprehensive frequency report"""
        
        # Create lookup for MIND skill metadata
        skill_metadata = {
            skill['name']: skill 
            for skill in mind_skills
        }
        
        # Build detailed report
        report = {
            'total_jobs_analyzed': self.total_jobs,
            'total_unique_skills_found': len(skill_counts),
            'skills': []
        }
        
        for canonical_name, count in skill_counts.most_common():
            metadata = skill_metadata.get(canonical_name, {})
            
            skill_info = {
                'canonical_name': canonical_name,
                'job_count': count,
                'frequency_pct': round((count / self.total_jobs) * 100, 2),
                'skill_type': metadata.get('type', []),
                'technical_domains': metadata.get('technicalDomains', []),
                'synonyms': metadata.get('synonyms', [])
            }
            
            report['skills'].append(skill_info)
        
        # Add summary statistics
        thresholds = [1, 5, 10, 50, 100]
        report['summary'] = {}
        
        for threshold in thresholds:
            above_threshold = sum(1 for count in skill_counts.values() 
                                 if count >= threshold)
            report['summary'][f'skills_above_{threshold}'] = above_threshold
        
        return report
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def filter_mind_by_frequency(mind_skills: List[dict], 
                             skill_counts: Counter,
                             min_count: int = 10) -> List[dict]:
    """Filter MIND skills to only those appearing >= min_count times"""
    
    filtered = []
    
    for skill in mind_skills:
        canonical_name = skill.get('name')
        count = skill_counts.get(canonical_name, 0)
        
        if count >= min_count:
            # Add frequency metadata
            skill['_frequency'] = count
            filtered.append(skill)
    
    print(f"\nFiltering results:")
    print(f"  Original skills: {len(mind_skills)}")
    print(f"  Skills with >= {min_count} occurrences: {len(filtered)}")
    print(f"  Reduction: {100 - (len(filtered)/len(mind_skills)*100):.1f}%")
    
    return filtered


def main():
    parser = argparse.ArgumentParser(
        description='Analyze skill frequency in job corpus for MIND ontology filtering'
    )
    parser.add_argument(
        '--output',
        default='data/skill_frequency.json',
        help='Output JSON file path'
    )
    parser.add_argument(
        '--min-frequency',
        type=int,
        default=10,
        help='Minimum job count to include skill (default: 10)'
    )
    parser.add_argument(
        '--mind-file',
        default='MIND-tech-ontology-main/__aggregated_skills.json',
        help='Path to MIND ontology JSON file'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("MIND Ontology Skill Frequency Analysis")
    print("=" * 70)
    
    # Initialize analyzer
    analyzer = SkillFrequencyAnalyzer(DB_CONFIG)
    
    try:
        # Load MIND ontology
        print(f"\n1. Loading MIND ontology from: {args.mind_file}")
        mind_skills = analyzer.load_mind_ontology(args.mind_file)
        print(f"   Loaded {len(mind_skills)} skills from MIND ontology")
        
        # Load job descriptions
        print("\n2. Loading job descriptions from database...")
        jobs = analyzer.get_all_job_descriptions()
        
        # Create search patterns
        print("\n3. Creating search patterns for all skills and synonyms...")
        patterns = analyzer.create_skill_patterns(mind_skills)
        
        # Analyze frequencies
        print("\n4. Analyzing skill frequencies in job corpus...")
        print("   (This may take a few minutes...)")
        skill_counts = analyzer.analyze_frequencies(jobs, patterns)
        
        # Generate report
        print("\n5. Generating frequency report...")
        report = analyzer.generate_report(skill_counts, mind_skills)
        
        # Save report
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✓ Report saved to: {output_path}")
        
        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY STATISTICS")
        print("=" * 70)
        print(f"Total jobs analyzed: {report['total_jobs_analyzed']:,}")
        print(f"Unique skills found: {report['total_unique_skills_found']:,}")
        print("\nSkills by frequency threshold:")
        for key, value in report['summary'].items():
            threshold = key.replace('skills_above_', '')
            print(f"  >= {threshold} jobs: {value:,} skills")
        
        # Show top 20 skills
        print("\nTop 20 most common skills:")
        for i, skill in enumerate(report['skills'][:20], 1):
            print(f"  {i:2d}. {skill['canonical_name']:30s} "
                  f"({skill['job_count']:4d} jobs, {skill['frequency_pct']:5.1f}%)")
        
        # Create filtered version
        if args.min_frequency > 1:
            print(f"\n6. Creating filtered MIND ontology (min frequency: {args.min_frequency})...")
            filtered_skills = filter_mind_by_frequency(
                mind_skills, 
                skill_counts, 
                args.min_frequency
            )
            
            filtered_output = output_path.parent / 'mind_skills_filtered.json'
            with open(filtered_output, 'w', encoding='utf-8') as f:
                json.dump(filtered_skills, f, indent=2)
            
            print(f"✓ Filtered skills saved to: {filtered_output}")
        
    finally:
        analyzer.close()
    
    print("\n" + "=" * 70)
    print("Analysis complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()
