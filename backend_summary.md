# InvenIO Backend: Core Systems & Usage Guide

InvenIO is a powerful backend designed for a decentralized intellectual property (IP) marketplace. It combines a custom internal blockchain ledger for immutability, an AI-driven duplicate detection engine, and a modern REST API built with **FastAPI**.

## 🚀 Getting Started

### 1. Environment Setup
Create a `.env` file in the `backend/` directory with the following variables:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/invenio
SECRET_KEY=your_secure_random_key
PINATA_API_KEY=your_pinata_key
PINATA_SECRET_API_KEY=your_pinata_secret
RAZORPAY_KEY_ID=your_razorpay_id
RAZORPAY_KEY_SECRET=your_razorpay_secret
```

### 2. Installation
Install the dependencies using `pip`:
```bash
pip install -r requirements.txt
```

### 3. Running the Server
Start the development server with:
```bash
uvicorn app.main:app --reload --port 8000
```

---

## 🔗 Internal Blockchain Ledger
The backend maintains an internal ledger (`app/blockchain`) to track all IP-related transactions (claims, transfers, payments) ensuring auditability.

**Example: Adding a Transaction**
```python
from app.blockchain.blockchain import invenio_ledger
from app.blockchain.transaction import Transaction

# Create a new transaction
tx = Transaction(
    sender="user_wallet_address",
    recipient="marketplace_contract",
    amount=100.0,
    data={"action": "PATENT_TOKENIZATION", "idea_id": 5}
)

# Add to pending and "mine" the block
invenio_ledger.add_transaction(tx)
new_block = invenio_ledger.mine_pending_transactions()

print(f"Block {new_block.index} added with hash: {new_block.hash}")
```

---

## 🧠 AI Similarity Engine
InvenIO uses NLP models (`sentence-transformers`) to detect duplicate patent ideas before they are tokenized, protecting the integrity of the marketplace.

**Example: Detecting Duplicates**
```python
from app.ai.duplicate_detector import duplicate_detector

new_idea_text = "A blockchain-powered system for managing intellectual property rights."
existing_ideas = [
    "A platform for IP management using distributed ledgers.",
    "A food delivery app using drones."
]

# 1. Generate embeddings
new_emb = duplicate_detector.generate_embedding(new_idea_text)
existing_embs = [duplicate_detector.generate_embedding(txt) for txt in existing_ideas]

# 2. Check similarity scores
scores = duplicate_detector.calculate_similarity(new_emb, existing_embs)
# scores will be [0.92, 0.15] - indicating the first one is a likely duplicate.
```

---

## 💎 Idea Tokenization Workflow
The tokenization of a patent is a multi-step process that ensures the idea is unique, stored securely, and recorded on the ledger.

1.  **AI Duplicate Check**: The text is embedded and compared against all existing idea vectors. If similarity > 85%, the idea is rejected.
2.  **IPFS Storage**: Any uploaded diagrams or technical documents are sent to **Pinata (IPFS)** to obtain a permanent CID (Hash).
3.  **Database Recording**: The idea metadata (Title, Price, Category, IPFS CID) is stored in the relational database.
4.  **Blockchain Ledger Sync**: A transaction is created recording the "Tokenization" event, including the IPFS CID and the minting fee, which is then mined into a block.

---

## 📂 Project Structure
- **/app/main.py**: Entry point & API routing.
- **/app/routes**: REST endpoints (auth, wallet, ideas, marketplace).
- **/app/blockchain**: Internal distributed ledger implementation.
- **/app/ai**: Semantic similarity & duplicate detection logic.
- **/app/database**: SQLAlchemy models & database migrations.
- **/app/services**: Core business logic.
- **/app/config**: Global app settings and environment management.

## 🛡️ Authentication
All protected routes require a **JWT Bearer Token**. Authenticate via `/auth/login` to receive your access token.

---
*Created automatically by InvenIO Platform Management.*
