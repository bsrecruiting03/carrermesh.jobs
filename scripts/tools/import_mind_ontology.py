"""
MIND Ontology Import Script (Phase 1 + Phase 2)
================================================

Imports filtered MIND Tech Ontology skills into PostgreSQL database.

Phase 1 Files:
- programming_languages.json
- frameworks_frontend.json
- frameworks_backend.json
- databases.json

Phase 2 Files:
- libraries_javascript.json
- libraries_python.json
- tools.json

Usage:
    # First, run frequency analysis
    python scripts/analyze_skill_frequency.py --output data/skill_frequency.json
    
    # Then import filtered skills
    python scripts/import_mind_ontology.py --min-frequency 10

Arguments:
    --min-frequency: Minimum job count to import skill (default: 10)
    --batch-size: Number of skills to insert per batch (default: 100)
    --dry-run: Preview what would be imported without making changes
"""

import json
import psycopg2
from psycopg2.extras import execute_batch
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict
import argparse

# Database connection - use same as existing codebase
import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5433/job_board")

# Phase 1 + 2 files to import
ONTOLOGY_FILES = {
    'phase1': [
        'MIND-tech-ontology-main/skills/programming_languages.json',
        'MIND-tech-ontology-main/skills/frameworks_frontend.json',
        'MIND-tech-ontology-main/skills/frameworks_backend.json',
        'MIND-tech-ontology-main/skills/databases.json',
    ],
    'phase2': [
        'MIND-tech-ontology-main/skills/libraries_javascript.json',
        'MIND-tech-ontology-main/skills/libraries_python.json',
        'MIND-tech-ontology-main/skills/tools.json',
    ]
}

CONCEPT_FILES = [
    'MIND-tech-ontology-main/concepts/application_tasks.json',
    'MIND-tech-ontology-main/concepts/architectural_patterns.json',
    'MIND-tech-ontology-main/concepts/technical_domains.json',
]


class MINDImporter:
    """Imports MIND ontology into PostgreSQL"""
    
    def __init__(self, min_frequency: int = 10):
        """
        Initialize MIND importer with database connection
        
        Args:
            min_frequency: Minimum times a skill must appear to be imported
        """
        self.min_frequency = min_frequency
        self.conn = psycopg2.connect(DATABASE_URL)
        self.frequency_data = {}
        self.concept_name_to_id = {}
        
        # Statistics
        self.skills_imported = 0
        self.concepts_imported = 0
        self.relationships_created = 0
        
    def load_frequency_data(self, frequency_file: str):
        """Load skill frequency analysis results"""
        if not Path(frequency_file).exists():
            print(f"Warning: Frequency file not found: {frequency_file}")
            print("All skills will be imported (no filtering)")
            return
        
        with open(frequency_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create lookup: canonical_name -> frequency
        for skill in data.get('skills', []):
            self.frequency_data[skill['canonical_name']] = skill['job_count']
        
        print(f"Loaded frequency data for {len(self.frequency_data)} skills")
    
    def should_import_skill(self, canonical_name: str) -> bool:
        """Check if skill meets frequency threshold"""
        if not self.frequency_data:
            return True  # No filtering if no frequency data
        
        freq = self.frequency_data.get(canonical_name, 0)
        return freq >= self.min_frequency
    
    def load_ontology_file(self, file_path: str) -> List[dict]:
        """Load skills from a single MIND JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both array and object formats
        if isinstance(data, list):
            return data
        else:
            return data.get('skills', [])
    
    def import_concepts(self, concept_files: List[str], dry_run: bool = False) -> Dict[str, int]:
        """Import concepts from MIND ontology"""
        all_concepts = []
        
        for file_path in concept_files:
            if not Path(file_path).exists():
                print(f"Warning: Concept file not found: {file_path}")
                continue
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Determine category from filename
            file_category = Path(file_path).stem  # e.g., 'application_tasks'
            
           #Handle MIND concept file structure: array of {category, tasks}
            if isinstance(data, list):
                for entry in data:
                    if isinstance(entry, dict) and 'tasks' in entry:
                        # MIND format: {category: "...", tasks: ["..."]}
                        category = entry.get('category', file_category)
                        for task_name in entry.get('tasks', []):
                            if task_name and isinstance(task_name, str):
                                all_concepts.append({
                                    'name': task_name,
                                    '_category': file_category,
                                    'synonyms': [],
                                    'description': f"Task in {category}"
                                })
                    elif isinstance(entry, str):
                        # Simple string list
                        all_concepts.append({
                            'name': entry,
                            '_category': file_category,
                            'synonyms': [],
                            'description': ''
                        })
                    elif isinstance(entry, dict) and 'name' in entry:
                        # Full concept dict
                        entry_copy = entry.copy()
                        entry_copy['_category'] = file_category
                        all_concepts.append(entry_copy)
            else:
                # Object format
                concepts = data.get('concepts', [])
                for concept in concepts:
                    if isinstance(concept, str):
                        all_concepts.append({
                            'name': concept,
                            '_category': file_category,
                            'synonyms': [],
                            'description': ''
                        })
                    elif isinstance(concept, dict):
                        concept_copy = concept.copy()
                        concept_copy['_category'] = file_category
                        all_concepts.append(concept_copy)
        
        print(f"\nImporting {len(all_concepts)} concepts...")
        
        if dry_run:
            print("DRY RUN: Would import concepts:")
            for i, concept in enumerate(all_concepts[:10]):
                print(f"  {i+1}. {concept.get('name')} ({concept['_category']})")
            if len(all_concepts) > 10:
                print(f"  ... and {len(all_concepts) - 10} more")
            return {}
        
        # Insert concepts
        cur = self.conn.cursor()
        
        concept_data = []
        for concept in all_concepts:
            concept_data.append((
                concept.get('name'),
                concept.get('_category'),
                concept.get('synonyms', []),
                concept.get('description', '')
            ))
        
        execute_batch(cur, """
            INSERT INTO concepts (name, category, synonyms, description)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE
            SET category = EXCLUDED.category,
                synonyms = EXCLUDED.synonyms,
                description = EXCLUDED.description,
                updated_at = NOW()
        """, concept_data)
        
        # Build concept name -> ID mapping
        cur.execute("SELECT name, concept_id FROM concepts")
        self.concept_name_to_id = dict(cur.fetchall())
        
        self.conn.commit()
        cur.close()
        
        print(f"✓ Imported {len(all_concepts)} concepts")
        return self.concept_name_to_id
    
    def import_skills(self, file_paths: List[str], dry_run: bool = False) -> int:
        """Import skills from MIND ontology files"""
        all_skills = []
        
        # Load all skills from files
        for file_path in file_paths:
            if not Path(file_path).exists():
                print(f"Warning: File not found: {file_path}")
                continue
            
            skills = self.load_ontology_file(file_path)
            all_skills.extend(skills)
        
        print(f"\nLoaded {len(all_skills)} total skills from {len(file_paths)} files")
        
        # Filter by frequency
        filtered_skills = [
            skill for skill in all_skills
            if self.should_import_skill(skill.get('name', ''))
        ]
        
        print(f"After frequency filtering (>= {self.min_frequency} occurrences): "
              f"{len(filtered_skills)} skills")
        
        if dry_run:
            print("\nDRY RUN: Would import the following skills:")
            for i, skill in enumerate(filtered_skills[:20]):
                freq = self.frequency_data.get(skill.get('name'), 0)
                print(f"  {i+1}. {skill.get('name'):30s} "
                      f"(type: {skill.get('type', ['Unknown'])[0]}, freq: {freq})")
            if len(filtered_skills) > 20:
                print(f"  ... and {len(filtered_skills) - 20} more")
            return 0
        
        # Prepare data for insertion
        skill_data = []
        skill_name_to_index = {}  # for resolving implies_skills later
        
        for idx, skill in enumerate(filtered_skills):
            skill_name_to_index[skill.get('name')] = idx
            
            # Normalize synonyms to lowercase
            synonyms = [s.lower() for s in skill.get('synonyms', [])]
            
            skill_data.append({
                'canonical_name': skill.get('name'),
                'skill_type': skill.get('type', []),
                'synonyms': synonyms,
                'technical_domains': skill.get('technicalDomains', []),
                'implies_skills_names': skill.get('impliesKnowingSkills', []),  # Will resolve to IDs later
                'application_tasks': skill.get('solvesApplicationTasks', []),
                'conceptual_aspects': skill.get('conceptualAspects', []),
                'architectural_patterns': skill.get('architecturalPatterns', []) or 
                                        skill.get('implementsPatternsByDefault', []),
                'build_tools': skill.get('buildTools', []),
                'metadata': {
                    'associated_domains': skill.get('associatedToApplicationDomains', []),
                    'runtime_environments': skill.get('runtimeEnvironments', []),
                    'source': 'mind_ontology_v1'
                }
            })
        
        # Insert skills (first pass - without implies_skills)
        print("\nInserting skills into database...")
        cur = self.conn.cursor()
        
        insert_data = [
            (
                s['canonical_name'],
                s['skill_type'],
                s['synonyms'],
                s['technical_domains'],
                [],  # implies_skills placeholder
                s['application_tasks'],
                s['conceptual_aspects'],
                s['architectural_patterns'],
                s['build_tools'],
                json.dumps(s['metadata'])
            )
            for s in skill_data
        ]
        
        execute_batch(cur, """
            INSERT INTO skills (
                canonical_name, skill_type, synonyms, technical_domains,
                implies_skills, application_tasks, conceptual_aspects,
                architectural_patterns, build_tools, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (canonical_name) DO UPDATE
            SET skill_type = EXCLUDED.skill_type,
                synonyms = EXCLUDED.synonyms,
                technical_domains = EXCLUDED.technical_domains,
                application_tasks = EXCLUDED.application_tasks,
                conceptual_aspects = EXCLUDED.conceptual_aspects,
                architectural_patterns = EXCLUDED.architectural_patterns,
                build_tools = EXCLUDED.build_tools,
                metadata = EXCLUDED.metadata,
                updated_at = NOW()
        """, insert_data, page_size=100)
        
        self.conn.commit()
        print(f"✓ Inserted {len(insert_data)} skills")
        
        # Second pass: Update implies_skills with actual IDs
        print("\nResolving skill relationships (implies_skills)...")
        
        # Get skill_id mapping
        cur.execute("SELECT canonical_name, skill_id FROM skills")
        name_to_id = dict(cur.fetchall())
        
        # Build updates for implies_skills
        update_data = []
        for s in skill_data:
            canonical_name = s['canonical_name']
            implies_names = s['implies_skills_names']
            
            # Resolve names to IDs
            implies_ids = []
            for implied_name in implies_names:
                if implied_name in name_to_id:
                    implies_ids.append(name_to_id[implied_name])
            
            if implies_ids:
                update_data.append((implies_ids, canonical_name))
        
        if update_data:
            execute_batch(cur, """
                UPDATE skills
                SET implies_skills = %s
                WHERE canonical_name = %s
            """, update_data)
            
            self.conn.commit()
            print(f"✓ Updated {len(update_data)} skills with relationship data")
        
        # Third pass: Create skill-concept mappings
        print("\nCreating skill-concept mappings...")
        skill_concept_data = []
        
        for s in skill_data:
            skill_id = name_to_id.get(s['canonical_name'])
            if not skill_id:
                continue
            
            for task_name in s['application_tasks']:
                concept_id = self.concept_name_to_id.get(task_name)
                if concept_id:
                    skill_concept_data.append((skill_id, concept_id, 'solves'))
            
            for pattern_name in s['architectural_patterns']:
                concept_id = self.concept_name_to_id.get(pattern_name)
                if concept_id:
                    skill_concept_data.append((skill_id, concept_id, 'implements'))
        
        if skill_concept_data:
            execute_batch(cur, """
                INSERT INTO skill_concepts (skill_id, concept_id, relationship_type)
                VALUES (%s, %s, %s)
                ON CONFLICT (skill_id, concept_id) DO NOTHING
            """, skill_concept_data)
            
            self.conn.commit()
            print(f"✓ Created {len(skill_concept_data)} skill-concept relationships")
        
        cur.close()
        return len(filtered_skills)
    
    def print_import_summary(self):
        """Print summary statistics after import"""
        cur = self.conn.cursor()
        
        print("\n" + "=" * 70)
        print("IMPORT SUMMARY")
        print("=" * 70)
        
        # Skill counts
        cur.execute("SELECT COUNT(*) FROM skills")
        total_skills = cur.fetchone()[0]
        print(f"Total skills in database: {total_skills:,}")
        
        # Skills by type
        cur.execute("""
            SELECT unnest(skill_type) AS type, COUNT(*)
            FROM skills
            GROUP BY type
            ORDER BY COUNT(*) DESC
        """)
        print("\nSkills by type:")
        for skill_type, count in cur.fetchall():
            print(f"  {skill_type:30s}: {count:4d}")
        
        # Concept counts
        cur.execute("SELECT COUNT(*) FROM concepts")
        total_concepts = cur.fetchone()[0]
        print(f"\nTotal concepts: {total_concepts:,}")
        
        # Skill-concept mappings
        cur.execute("SELECT COUNT(*) FROM skill_concepts")
        total_mappings = cur.fetchone()[0]
        print(f"Skill-concept mappings: {total_mappings:,}")
        
        # Skills with implied relationships
        cur.execute("""
            SELECT COUNT(*)
            FROM skills
            WHERE array_length(implies_skills, 1) > 0
        """)
        skills_with_implies = cur.fetchone()[0]
        print(f"\nSkills with 'implies' relationships: {skills_with_implies:,}")
        
        cur.close()
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Import MIND Tech Ontology into PostgreSQL (Phase 1 + 2)'
    )
    parser.add_argument(
        '--min-frequency',
        type=int,
        default=10,
        help='Minimum job count to import skill (default: 10)'
    )
    parser.add_argument(
        '--frequency-file',
        default='data/skill_frequency.json',
        help='Path to frequency analysis output'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview import without making database changes'
    )
    parser.add_argument(
        '--phase',
        choices=['1', '2', 'both'],
        default='both',
        help='Which phase files to import (default: both)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("MIND Tech Ontology Import (Phase 1 + 2)")
    print("=" * 70)
    
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No database changes will be made\n")
    # Initialize importer
    importer = MINDImporter(min_frequency=args.min_frequency)
    
    try:
        # Load frequency data
        print(f"Loading frequency data from: {args.frequency_file}")
        importer.load_frequency_data(args.frequency_file)
        
        # Determine which files to import
        files_to_import = []
        if args.phase in ['1', 'both']:
            files_to_import.extend(ONTOLOGY_FILES['phase1'])
        if args.phase in ['2', 'both']:
            files_to_import.extend(ONTOLOGY_FILES['phase2'])
        
        print(f"\nImporting from {len(files_to_import)} files:")
        for f in files_to_import:
            print(f"  - {Path(f).name}")
        
        # Import concepts first
        imported_concepts = importer.import_concepts(
            CONCEPT_FILES, 
            dry_run=args.dry_run
        )
        
        # Import skills
        imported_count = importer.import_skills(
            files_to_import,
            dry_run=args.dry_run
        )
        
        if not args.dry_run:
            # Print summary
            importer.print_import_summary()
            
            print("\n" + "=" * 70)
            print("✓ Import completed successfully!")
            print("=" * 70)
            print(f"\nNext steps:")
            print(f"1. Run backfill script to extract skills from existing jobs")
            print(f"2. Update SkillExtractor to use database ontology")
            print(f"3. Test search with hierarchical skill matching")
        else:
            print("\n" + "=" * 70)
            print("Dry run complete - no changes made")
            print("=" * 70)
            print(f"\nTo actually import, run without --dry-run flag")
    
    finally:
        importer.close()


if __name__ == '__main__':
    main()
