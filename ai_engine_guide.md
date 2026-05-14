# AI Engine Documentation: Semantic Similarity & NLP

The InvenIO platform utilizes advanced Natural Language Processing (NLP) to maintain marketplace integrity. This document explains the underlying technology, how to implement it, and how it can be adapted for other use cases.

## 🛠️ Technology Stack

The AI system is built using the following libraries:
- **Sentence-Transformers**: A Python framework for state-of-the-art sentence, text, and image embeddings.
- **Hugging Face**: The model is hosted on Hugging Face. We use the `all-MiniLM-L6-v2` model.
- **PyTorch**: The underlying engine for vector computations.

### Why `all-MiniLM-L6-v2`?
We use this specific model because it is **extremely fast**, **lightweight** (approx. 80MB), and specifically tuned for **semantic similarity**—understanding that "A tool for fixing cars" is similar to "Automotive repair equipment" even if they use different words.

---

## 🚀 How it Works (Implementation)

The system works in two phases: **Embedding** and **Comparison**.

### 1. The Detector Class
The core logic resides in `app/ai/duplicate_detector.py`. 

```python
from sentence_transformers import SentenceTransformer, util
import torch

class DuplicateDetector:
    def __init__(self):
        # Initializes the model (downloads automatically on first run)
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def generate_embedding(self, text: str):
        # Converts text into a 384-dimensional mathematical vector
        return self.model.encode(text, convert_to_tensor=True)

    def calculate_similarity(self, target_vector, library_vectors):
        # Uses Cosine Similarity to compare vectors
        # Returns a score between 0 (different) and 1 (identical)
        return util.cos_sim(target_vector, library_vectors)[0]
```

### 2. Integration in API
When a user uploads an idea, we combine the `title`, `description`, and `keywords` into a single string to create a "semantic fingerprint."

```python
# snippet from app/routes/idea_routes.py
combined_text = f"{title} {problem_statement} {solution}"
new_fingerprint = duplicate_detector.generate_embedding(combined_text)

# We then compare this fingerprint against all fingerprints saved in our database
scores = duplicate_detector.calculate_similarity(new_fingerprint, database_vectors)
if max(scores) > 0.85:
    return "Rejected: Similar idea already exists!"
```

---

## 💡 Using for Other Purposes

This AI engine isn't limited to just duplicate detection. Here are other ways to use it:

### A. Intelligent Search
Instead of searching for exact keywords, users can search for *concepts*.
*   **Query**: "Green Energy Solutions"
*   **Result**: Even if a patent doesn't contain "Green Energy," the AI will find "Sustainable Solar Panel Design" because they are semantically related.

### B. Auto-Categorization
You can use the AI to automatically assign categories to new ideas.
```python
categories = ["Medical", "Fintech", "SpaceTech", "AgriTech"]
cat_embeddings = [detector.generate_embedding(c) for c in categories]

new_idea = "A new way to plant rice using drones"
idea_emb = detector.generate_embedding(new_idea)

# The highest similarity score tells you the category (AgriTech)
scores = detector.calculate_similarity(idea_emb, cat_embeddings)
```

### C. Recommendation System
Show users "Related Patents" by finding ideas in the database with high similarity scores to the one they are currently viewing.

---

## 🛠️ Step-by-Step implementation Example

To use this AI in a new script:

1. **Install Dependencies**:
   ```bash
   pip install sentence-transformers torch
   ```

2. **Simple Script**:
   ```python
   from sentence_transformers import SentenceTransformer, util

   # 1. Load Model
   model = SentenceTransformer('all-MiniLM-L6-v2')

   # 2. Define your data
   base_text = "Universal remote for all smart devices"
   compare_texts = [
       "A controller that works with any IoT gadget", # Highly similar
       "A recipe for chocolate cake",                # Not similar
       "Smartphone app for home automation"          # Moderately similar
   ]

   # 3. Compute Embeddings
   base_emb = model.encode(base_text)
   compare_embs = model.encode(compare_texts)

   # 4. Get Scores
   cosine_scores = util.cos_sim(base_emb, compare_embs)[0]

   for i in range(len(compare_texts)):
       print(f"Similarity: {cosine_scores[i]:.4f} | Text: {compare_texts[i]}")
   ```

---
*Powered by InvenIO AI Engine*
