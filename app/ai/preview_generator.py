import re
import torch
from sentence_transformers import util
from app.ai.duplicate_detector import duplicate_detector

def generate_extractive_preview(title: str, text: str, num_sentences: int = 3) -> str:
    if not text or not text.strip():
        return ""
        
    # Basic sentence splitting
    sentences = re.split(r'(?<=[.!?]) +', text.strip())
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    if len(sentences) <= num_sentences:
        return text

    # Use the existing duplicate detector's model
    model = duplicate_detector.model
    
    # Encode all sentences
    sentence_embeddings = model.encode(sentences, convert_to_tensor=True)
    
    # We use the title + first few words as the query to find the most representative sentences
    query = title + " " + " ".join(sentences[:2])
    query_embedding = model.encode(query, convert_to_tensor=True)
    
    # Calculate similarities
    cos_scores = util.cos_sim(query_embedding, sentence_embeddings)[0]
    
    # Get top sentences
    top_results = torch.topk(cos_scores, k=min(num_sentences, len(sentences)))
    
    # Sort them back by their original order in the text to maintain flow
    top_indices = top_results[1].tolist()
    top_indices.sort()
    
    summary_sentences = [sentences[i] for i in top_indices]
    return " ".join(summary_sentences)
