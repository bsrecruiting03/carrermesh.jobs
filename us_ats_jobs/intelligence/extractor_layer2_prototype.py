
import os
import json
import time
import logging
from typing import List, Dict, Tuple
try:
    from sentence_transformers import SentenceTransformer, util
    import torch
except ImportError:
    print("⚠️  sentence-transformers not installed. Run 'pip install sentence-transformers'")
    SentenceTransformer = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Layer2Prototype")

class Layer2VectorExtractor:
    def __init__(self, ontology_path: str = None, model_name: str = 'all-MiniLM-L6-v2'):
        if not SentenceTransformer:
            raise ImportError("sentence-transformers library is missing.")
            
        logger.info(f"🧠 Loading Vector Model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        self.ontology_path = ontology_path or self._find_ontology_path()
        
        self.skill_names = []
        self.skill_embeddings = None
        self._load_and_encode_ontology()

    def _find_ontology_path(self) -> str:
        # Navigate up from us_ats_jobs/intelligence/extractor_layer2_prototype.py
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        possible_path = os.path.join(base_dir, "MIND-tech-ontology-main", "__aggregated_skills.json")
        if os.path.exists(possible_path):
            return possible_path
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "taxonomy.json")

    def _load_and_encode_ontology(self):
        """
        Loads extraction targets and pre-computes their embeddings.
        For prototype, we only load a subset to keep it fast.
        """
        if not os.path.exists(self.ontology_path):
            logger.error(f"❌ Ontology file missing: {self.ontology_path}")
            return

        logger.info("📚 Loading Ontology for Vectorization...")
        with open(self.ontology_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Collect Canonical Names + Synonyms
        candidates = set()
        if isinstance(data, list):
            # MIND Format
            for item in data[:2000]: # LIMIT for prototype speed
                candidates.add(item.get("name"))
                # optionally add synonyms
        elif isinstance(data, dict):
            # Taxonomy Format
             for cat, subcats in data.items():
                for sub, skills in subcats.items():
                    for match, _ in skills.items():
                        candidates.add(match)

        self.skill_names = list(candidates)
        logger.info(f"🔢 Encoding {len(self.skill_names)} skills (one-time setup)...")
        
        start = time.time()
        self.skill_embeddings = self.model.encode(self.skill_names, convert_to_tensor=True)
        end = time.time()
        logger.info(f"✅ Ontology Vectorized in {end - start:.2f}s")

    def extract(self, text: str, threshold: float = 0.6) -> List[Tuple[str, float]]:
        """
        Semantic Search: Find skills in text that match ontology concepts.
        """
        if not text or self.skill_embeddings is None:
            return []

        # 1. Chunk Text? For prototype, we just encode the whole sentence or entities
        # Better approach for NER: Split text into phrases or use N-grams.
        # But for "Semantic Matching", we often check if *sentences* mention *skills*.
        # A simpler prototype approach: Compare existing extracted entities (from Regex) 
        # against ontology to correct them? 
        # OR: Sliding window over text.
        
        # Let's try matching Keywords found by simple split/NER against Ontology
        # to find "Fuzzy Matches" (e.g. "React JS" -> "React")
        # BUT Layer 2 is supposed to find things Layer 1 missed.
        
        # PROTOTYPE STRATEGY: 
        # Encode N-grams of input text and find closest ontology match.
        # This is slow O(N_text * M_ontology).
        
        # Let's just demonstrate "Concept Matching":
        # Input: "Experience in Neural Networks and Deep Learning frameworks."
        # We check if these phrases match "Artificial Intelligence" or "PyTorch" in ontology.
        
        # For simplicity, we assume we have a candidate list (e.g. noun phrases)
        # or we just match the query text against skills directly (if query is short).
        
        # Let's assume input text is a list of potential skills/phrases for this test.
        # Real impl would use Spacy to get Noun Chunks first.
        
        return []

    def verify_match(self, candidate_text: str) -> None:
        """
        Demonstrates the power: Matches input text to closest ontology skill.
        """
        logger.info(f"\n🔍 Query: '{candidate_text}'")
        query_embedding = self.model.encode(candidate_text, convert_to_tensor=True)
        
        # Semantic Search
        hits = util.semantic_search(query_embedding, self.skill_embeddings, top_k=3)
        
        for hit in hits[0]:
            idx = hit['corpus_id']
            score = hit['score']
            skill = self.skill_names[idx]
            logger.info(f"   --> Match: '{skill}' (Score: {score:.4f})")

if __name__ == "__main__":
    # Test Block
    print("🚀 Initializing Layer 2 Prototype...")
    try:
        extractor = Layer2VectorExtractor()
        
        # Test Cases: Fuzzy / Concept Matching
        # 1. Exact-ish
        extractor.verify_match("reactjs") 
        
        # 2. Typos
        extractor.verify_match("Pytorch framework") # Should match PyTorch
        
        # 3. Concepts
        extractor.verify_match("Amazon Cloud") # Should match AWS
        
        # 4. Acronym vs Full
        extractor.verify_match("Machine Learning Ops") # Should match MLOps
        
    except ImportError:
        print("Skipping test (dependencies missing)")
