"""
ML-Based Semantic Matching using BioBERT
Provides advanced semantic similarity for NAMASTE-ICD11 mapping
"""

from sentence_transformers import SentenceTransformer, util
import numpy as np
from typing import List, Dict, Tuple
import pickle
import os

class SemanticMatcher:
    def __init__(self, model_name: str = 'dmis-lab/biobert-base-cased-v1.2'):
        """
        Initialize BioBERT model for biomedical text similarity
        Falls back to lighter model if BioBERT unavailable
        """
        try:
            self.model = SentenceTransformer(model_name)
            print(f"✅ Loaded BioBERT model: {model_name}")
        except Exception as e:
            print(f"⚠️ BioBERT unavailable, using fallback model: {e}")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        self.cache_dir = 'ml_models/embeddings_cache'
        os.makedirs(self.cache_dir, exist_ok=True)
        self.embeddings_cache = {}
    
    def encode_text(self, text: str) -> np.ndarray:
        """Generate embedding for given text"""
        # Check cache first
        cache_key = hash(text)
        if cache_key in self.embeddings_cache:
            return self.embeddings_cache[cache_key]
        
        # Generate new embedding
        embedding = self.model.encode(text, convert_to_tensor=True)
        self.embeddings_cache[cache_key] = embedding
        
        return embedding
    
    def compute_similarity(self, text1: str, text2: str) -> float:
        """Compute semantic similarity between two texts"""
        emb1 = self.encode_text(text1)
        emb2 = self.encode_text(text2)
        
        similarity = util.pytorch_cos_sim(emb1, emb2).item()
        return round(similarity, 4)
    
    def find_best_matches(self, 
                         query_text: str, 
                         candidate_texts: List[Dict[str, str]], 
                         top_k: int = 5) -> List[Dict]:
        """
        Find top-k most semantically similar texts
        
        Args:
            query_text: NAMASTE disease description
            candidate_texts: List of ICD-11 entries with 'code' and 'display'
            top_k: Number of top matches to return
        
        Returns:
            List of matches with similarity scores
        """
        query_embedding = self.encode_text(query_text)
        
        matches = []
        for candidate in candidate_texts:
            # Combine code display and description for better matching
            candidate_text = f"{candidate.get('display', '')} {candidate.get('definition', '')}"
            candidate_embedding = self.encode_text(candidate_text)
            
            similarity = util.pytorch_cos_sim(query_embedding, candidate_embedding).item()
            
            matches.append({
                'code': candidate.get('code'),
                'display': candidate.get('display'),
                'similarity': round(similarity, 4),
                'match_type': 'semantic'
            })
        
        # Sort by similarity and return top-k
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        return matches[:top_k]
    
    def hybrid_match(self, 
                    namaste_term: Dict, 
                    icd_candidates: List[Dict],
                    fuzzy_score_weight: float = 0.4,
                    semantic_score_weight: float = 0.6) -> List[Dict]:
        """
        Hybrid matching combining fuzzy and semantic approaches
        
        Args:
            namaste_term: NAMASTE entry with display, synonyms, description
            icd_candidates: ICD-11 candidate entries with scores
            fuzzy_score_weight: Weight for fuzzy matching (0-1)
            semantic_score_weight: Weight for semantic matching (0-1)
        
        Returns:
            Re-ranked candidates with hybrid scores
        """
        # Build comprehensive query text
        query_text = f"{namaste_term['display']} {namaste_term['description']}"
        if namaste_term.get('synonyms'):
            query_text += " " + " ".join(namaste_term['synonyms'])
        
        query_embedding = self.encode_text(query_text)
        
        enhanced_candidates = []
        for candidate in icd_candidates:
            # Get fuzzy score (if already computed)
            fuzzy_score = candidate.get('confidence', 0.5)
            
            # Compute semantic score
            candidate_text = f"{candidate.get('display', '')} {candidate.get('definition', '')}"
            candidate_embedding = self.encode_text(candidate_text)
            semantic_score = util.pytorch_cos_sim(query_embedding, candidate_embedding).item()
            
            # Hybrid score
            hybrid_score = (fuzzy_score * fuzzy_score_weight + 
                          semantic_score * semantic_score_weight)
            
            enhanced_candidates.append({
                **candidate,
                'fuzzy_score': round(fuzzy_score, 4),
                'semantic_score': round(semantic_score, 4),
                'hybrid_score': round(hybrid_score, 4),
                'confidence': round(hybrid_score, 4),  # Update confidence
                'match_method': 'hybrid'
            })
        
        # Sort by hybrid score
        enhanced_candidates.sort(key=lambda x: x['hybrid_score'], reverse=True)
        return enhanced_candidates
    
    def save_cache(self, filepath: str = None):
        """Save embeddings cache to disk"""
        if filepath is None:
            filepath = os.path.join(self.cache_dir, 'embeddings_cache.pkl')
        
        with open(filepath, 'wb') as f:
            pickle.dump(self.embeddings_cache, f)
        print(f"💾 Saved embeddings cache to {filepath}")
    
    def load_cache(self, filepath: str = None):
        """Load embeddings cache from disk"""
        if filepath is None:
            filepath = os.path.join(self.cache_dir, 'embeddings_cache.pkl')
        
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                self.embeddings_cache = pickle.load(f)
            print(f"📂 Loaded embeddings cache from {filepath}")
        else:
            print("ℹ️ No cache file found, starting fresh")


# Example usage
if __name__ == "__main__":
    matcher = SemanticMatcher()
    
    # Test similarity
    text1 = "Diabetes mellitus with high blood sugar"
    text2 = "Prameha - sweet urine disease with excess urination"
    
    similarity = matcher.compute_similarity(text1, text2)
    print(f"Similarity: {similarity}")
    
    # Test matching
    query = "Fever with intermittent pattern similar to malaria"
    candidates = [
        {"code": "1F40", "display": "Malaria", "definition": "Parasitic infection"},
        {"code": "MG26", "display": "Fever unspecified", "definition": "Body temperature elevation"},
        {"code": "1F41", "display": "Dengue fever", "definition": "Viral fever"}
    ]
    
    matches = matcher.find_best_matches(query, candidates, top_k=3)
    for match in matches:
        print(f"{match['code']}: {match['display']} - Similarity: {match['similarity']}")