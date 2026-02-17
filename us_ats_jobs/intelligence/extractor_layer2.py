
import os
import json
import time
import logging
from typing import List, Dict, Tuple
import pickle

# Lazy import
# Lazy import
try:
    from sentence_transformers import SentenceTransformer, util
    import torch
except (ImportError, RuntimeError, Exception) as e:
    logging.warning(f"⚠️ Vector Extractor disabled due to import error: {e}")
    SentenceTransformer = None

logger = logging.getLogger("Layer2Extractor")

class Layer2VectorExtractor:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Layer2VectorExtractor, cls).__new__(cls)
        return cls._instance

    def __init__(self, ontology_path: str = None, model_name: str = 'BAAI/bge-small-en-v1.5'):
        if hasattr(self, 'initialized'): return
        
        if not SentenceTransformer:
            logger.error("❌ sentence-transformers missing. Layer 2 disabled.")
            self.model = None
            return

        logger.info(f"🧠 Layer 2: Loading Neural Model {model_name}...")
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = SentenceTransformer(model_name, device=self.device)
        
        self.ontology_path = ontology_path or self._find_ontology_path()
        self.cache_path = os.path.join(os.path.dirname(self.ontology_path), "layer2_vector_cache_bge.pkl")
        
        self.skill_names = []
        self.skill_embeddings = None
        
        self._load_and_encode_ontology()
        self.initialized = True

    def _find_ontology_path(self) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        possible_path = os.path.join(base_dir, "MIND-tech-ontology-main", "__aggregated_skills.json")
        if os.path.exists(possible_path):
            return possible_path
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "taxonomy.json")

    def _load_and_encode_ontology(self):
        """
        Loads ontology and computes/loads vectors.
        """
        if not os.path.exists(self.ontology_path):
            logger.error(f"❌ Ontology file missing: {self.ontology_path}")
            return
            
        # 1. Try Loading Cache
        if os.path.exists(self.cache_path):
            try:
                logger.info(f"📀 Loading Vector Cache from {self.cache_path}...")
                with open(self.cache_path, 'rb') as f:
                    cache_data = pickle.load(f)
                    self.skill_names = cache_data['names']
                    self.skill_embeddings = cache_data['embeddings']
                logger.info(f"✅ Loaded {len(self.skill_names)} skills from cache.")
                return
            except Exception as e:
                logger.warning(f"⚠️ Failed to load cache: {e}. Recomputing.")

        # 2. Compute from Scratch
        logger.info("📚 Parsing Ontology for Vectorization (this occurs once)...")
        with open(self.ontology_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        candidates = set()
        # Parse MIND or Taxonomy
        if isinstance(data, list):
            for item in data:
                candidates.add(item.get("name"))
                # Synonyms? Maybe too noisy for vectors. Let's stick to canonicals first.
                # Vectors handle synonyms naturally (that's the point).
        elif isinstance(data, dict):
             for cat, subcats in data.items():
                for sub, skills in subcats.items():
                    for match, _ in skills.items():
                        candidates.add(match)

        self.skill_names = list(candidates)
        logger.info(f"🔢 Encoding {len(self.skill_names)} skills... (Please wait)")
        
        start = time.time()
        # Ensure instructions for retrieval if needed by model, usually BGE works fine without prefixes for symmetric tasks
        # But for asymmetric (Query vs Doc), instruction is needed. Here we stick to symmetric skill-to-skill match.
        self.skill_embeddings = self.model.encode(self.skill_names, convert_to_tensor=True, show_progress_bar=True)
        end = time.time()
        logger.info(f"✅ Vectors Computed in {end - start:.2f}s")
        
        # 3. Save Cache
        try:
            with open(self.cache_path, 'wb') as f:
                pickle.dump({'names': self.skill_names, 'embeddings': self.skill_embeddings}, f)
            logger.info("💾 Vector Cache Saved.")
        except Exception as e:
            logger.warning(f"⚠️ Could not save vector cache: {e}")

    def extract(self, text: str, threshold: float = 0.70) -> List[str]:
        """
        Finds skills in text using Semantic Search with Sliding Window.
        """
        if not text or self.model is None or self.skill_embeddings is None:
            return []

        # Sliding Window Split
        words = text.split()
        window_size = 64
        stride = 32
        chunks = []
        
        if len(words) <= window_size:
            chunks.append(text)
        else:
            for i in range(0, len(words), stride):
                chunk = " ".join(words[i:i + window_size])
                chunks.append(chunk)
                if i + window_size >= len(words):
                    break

        found_skills = set()
        
        # Encode chunks
        chunk_embeddings = self.model.encode(chunks, convert_to_tensor=True)
        
        # Search
        # BGE score distribution is different, usually needs higher threshold
        hits = util.semantic_search(chunk_embeddings, self.skill_embeddings, top_k=3, score_function=util.cos_sim)
        
        for chunk_hits in hits:
            for hit in chunk_hits:
                if hit['score'] > threshold:
                    skill_name = self.skill_names[hit['corpus_id']]
                    found_skills.add(skill_name)
                    
        return list(found_skills)

    def embed_text(self, text: str) -> List[float]:
        """
        Generates a vector embedding for the given text.
        Used for job description embedding (Hybrid Search).
        """
        if not text or self.model is None:
            return []
            
        try:
            # Generate embedding
            # normalize_embeddings=True is important for cosine similarity
            embedding = self.model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"❌ Error embedding text: {e}")
            return []

# Global Instance
_extractor = None

def extract_skills_semantic(text: str) -> List[str]:
    global _extractor
    if _extractor is None:
        _extractor = Layer2VectorExtractor()
    return _extractor.extract(text)
