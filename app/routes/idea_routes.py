from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database import models
from app.schemas import idea_schema
from app.routes.dependencies import get_current_user
from app.utils.ipfs_client import upload_to_ipfs
from app.ai.duplicate_detector import duplicate_detector
from app.blockchain.blockchain import invenio_ledger
from app.blockchain.transaction import Transaction
from app.utils.hashing import verify_password
from app.utils.email import notify_system_fee

router = APIRouter(prefix="/api/ideas", tags=["Ideas"])

from pydantic import BaseModel
class PreviewRequest(BaseModel):
    title: str
    problem_statement: str
    solution: str
    research_info: str
    keywords: str

@router.post("/generate-preview")
def generate_preview(payload: PreviewRequest, current_user: models.User = Depends(get_current_user)):
    from app.ai.preview_generator import generate_extractive_preview
    combined_text = f"{payload.problem_statement} {payload.solution} {payload.research_info}"
    snippet = generate_extractive_preview(payload.title, combined_text, num_sentences=3)
    return {"snippet": snippet}

@router.post("/check-duplicate", response_model=idea_schema.DuplicateCheckResponse)
def check_duplicate(payload: dict, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    combined_text = (
        f"{payload.get('title', '')} "
        f"{payload.get('problem_statement', '')} "
        f"{payload.get('solution', '')} "
        f"{payload.get('keywords', '')}"
    )
    new_embedding = duplicate_detector.generate_embedding(combined_text)
    
    existing_vectors = db.query(models.IdeaVector).all()
    if not existing_vectors:
        return {"is_duplicate": False, "similarity_score": 0.0, "message": "No duplicates found.", "similar_idea_id": None}
        
    embeddings_list = [v.embedding for v in existing_vectors]
    scores = duplicate_detector.calculate_similarity(new_embedding, embeddings_list)
    
    # Find max similarity
    max_score = max(scores) if scores else 0.0
    if max_score > 0.80:
        index = scores.index(max_score)
        similar_id = existing_vectors[index].idea_id
        return {"is_duplicate": True, "similarity_score": max_score, "message": "Similar idea already exists (>80% similarity).", "similar_idea_id": similar_id}
        
    return {"is_duplicate": False, "similarity_score": max_score, "message": "Idea is unique enough.", "similar_idea_id": None}

@router.post("/upload")
async def upload_idea(
    title: str = Form(...),
    snippet: str = Form(None),
    problem_statement: str = Form(...),
    research_info: str = Form(...),
    solution: str = Form(...),
    keywords: str = Form(...),
    category: str = Form(...),
    sale_type: str = Form("both"),
    price: float = Form(...),
    plan_1m_price: float = Form(None),
    plan_3m_price: float = Form(None),
    plan_6m_price: float = Form(None),
    password: str = Form(...), # Require exact password for PoW
    problem_id: str = Form(None), # Optional link to a problem statement
    file: UploadFile = File(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Check Duplicates Again
    combined_text = f"{title} {problem_statement} {solution} {keywords}"
    new_embedding = duplicate_detector.generate_embedding(combined_text)
    
    existing_vectors = db.query(models.IdeaVector).all()
    if existing_vectors:
        embeddings_list = [v.embedding for v in existing_vectors]
        scores = duplicate_detector.calculate_similarity(new_embedding, embeddings_list)
        if scores and max(scores) > 0.85: # stricter on actual upload
            raise HTTPException(status_code=400, detail="Idea rejected. A highly similar idea already exists in the system.")
            
    # Verify PIN/Password to authorize the transaction hash
    if not verify_password(password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid Account PIN/Password. Transaction Rejected.")
            
    fee_structure = {
        "Technology": 15.0,
        "Finance": 20.0,
        "Healthcare": 25.0,
        "Energy": 10.0,
        "Other": 5.0
    }
    mint_fee = 0.0 if float(price) == 0.0 else fee_structure.get(category, 5.0)

    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    if not wallet or wallet.balance < mint_fee:
        raise HTTPException(status_code=400, detail=f"Insufficient InvenIO balance. Tokenizing a {category} idea requires {mint_fee} Ʉ.")

    # Deduct the minting fee from the user's wallet (Proof of Work/System Burn)
    wallet.balance -= mint_fee
    
    # Create DB transaction for the fee
    fee_tx = models.Transaction(
        from_wallet=wallet.wallet_id,
        to_wallet=None,  # Consumed by the system
        amount=mint_fee,
        tx_hash="pending"
    )
    db.add(fee_tx)

    # 3. IPFS Storage for any diagrams
    ipfs_cid = None
    if file:
        file_bytes = await file.read()
        ipfs_cid = upload_to_ipfs(file_bytes, file.filename)

    # 3. Create DB Record
    new_idea = models.Idea(
        title=title, snippet=snippet, problem_statement=problem_statement, research_info=research_info,
        solution=solution, keywords=keywords, category=category, sale_type=sale_type, price=price,
        plan_1m_price=plan_1m_price, plan_3m_price=plan_3m_price, plan_6m_price=plan_6m_price,
        owner_id=current_user.id, ipfs_hash=ipfs_cid,
        problem_id=problem_id if problem_id else None
    )
    db.add(new_idea)
    db.commit()
    db.refresh(new_idea)
    
    # 4. Save Vector
    new_vector = models.IdeaVector(idea_id=new_idea.idea_id, embedding=new_embedding)
    db.add(new_vector)
    db.commit()
    
    # 6. Add to Blockchain Ledger
    blockchain_tx = Transaction(
        from_wallet=str(current_user.wallet.wallet_id) if current_user.wallet else "System", 
        to_wallet="System", 
        amount=mint_fee,  # Use the dynamically calculated fee as the network cost
        tx_type="idea_creation",
        metadata={"idea_id": str(new_idea.idea_id), "ipfs": ipfs_cid, "timestamp": new_idea.created_at.isoformat()}
    )
    tx_hash = invenio_ledger.add_transaction(blockchain_tx)
    invenio_ledger.mine_pending_transactions()
    
    # Update fee transaction hash with the real blockchain hash
    fee_tx.tx_hash = tx_hash
    db.commit()

    # Send Notification Email
    notify_system_fee(current_user.email, mint_fee, f"Tokenization of '{title}'")

    return new_idea

@router.put("/{idea_id}/pricing", response_model=idea_schema.IdeaResponse)
def update_idea_pricing(idea_id: str, payload: idea_schema.IdeaPricingUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    idea = db.query(models.Idea).filter(models.Idea.idea_id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
        
    if idea.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized to update this idea")
        
    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(idea, key, value)
        
    db.commit()
    db.refresh(idea)
    
    # Needs to be formatted properly for response
    setattr(idea, "is_unlocked", True)
    return idea
