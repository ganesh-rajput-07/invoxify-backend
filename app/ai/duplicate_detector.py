from sentence_transformers import SentenceTransformer, util
import torch

class DuplicateDetector:
    def __init__(self):
        # Load a lightweight, fast sentence-transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def generate_embedding(self, text: str) -> list[float]:
        """Convert combined idea text into a vector embedding."""
        embedding = self.model.encode(text, convert_to_tensor=True)
        return embedding.tolist()

    def calculate_similarity(self, new_embedding: list[float], existing_embeddings: list[list[float]]) -> list[float]:
        """Calculate cosine similarity between new idea and existing ideas."""
        if not existing_embeddings:
            return []
            
        new_tensor = torch.tensor(new_embedding)
        existing_tensor = torch.tensor(existing_embeddings)
        
        # Calculate cosine similarities
        cosine_scores = util.cos_sim(new_tensor, existing_tensor)[0]
        
        return cosine_scores.tolist()

duplicate_detector = DuplicateDetector()
