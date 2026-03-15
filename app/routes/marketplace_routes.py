from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database.connection import get_db
from app.database import models
from app.schemas import idea_schema
from app.routes.dependencies import get_current_user
from app.blockchain.blockchain import invox_ledger
from app.blockchain.transaction import Transaction
from app.utils.hashing import verify_password
from app.utils.email import notify_token_purchase
from typing import List
from pydantic import BaseModel

class BuyRequest(BaseModel):
    password: str

router = APIRouter(prefix="/api/marketplace", tags=["Marketplace"])

@router.get("/ideas", response_model=List[idea_schema.IdeaResponse])
def get_all_ideas(category: str = None, q: str = None, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(models.Idea)
    if category:
        query = query.filter(models.Idea.category == category)
    if q:
        search = f"%{q}%"
        query = query.filter(or_(models.Idea.title.ilike(search), models.Idea.keywords.ilike(search)))
        
    ideas_db = query.all()
    user_purchases = db.query(models.IdeaPurchase.idea_id).filter(models.IdeaPurchase.buyer_id == current_user.id).all()
    purchased_idea_ids = {p.idea_id for p in user_purchases}
    
    ideas_response = []
    for idea in ideas_db:
        # User has access if they are the original owner OR if they bought it
        is_unlocked = (idea.owner_id == current_user.id) or (idea.idea_id in purchased_idea_ids)
        
        # Assign directly to the SQLAlchemy object so Pydantic can parse standard attributes + relationships
        setattr(idea, "is_unlocked", is_unlocked)
        ideas_response.append(idea)

    return ideas_response

@router.post("/buy/{idea_id}")
def buy_idea(idea_id: str, payload: BuyRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Verify PIN/Password for PoW authorization
    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid Account PIN/Password. Transaction Rejected.")

    idea = db.query(models.Idea).filter(models.Idea.idea_id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
        
    if idea.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot buy your own idea")

    buyer_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    seller_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == idea.owner_id).first()
    
    if buyer_wallet.balance < idea.price:
        raise HTTPException(status_code=400, detail="Insufficient INVOX token balance")

    # 1. Update SQL Balances
    buyer_wallet.balance -= idea.price
    seller_wallet.balance += idea.price
    
    # 2. Add System Transaction
    new_tx = models.Transaction(
        from_wallet=buyer_wallet.wallet_id,
        to_wallet=seller_wallet.wallet_id,
        amount=idea.price,
        tx_hash="pending"
    )
    db.add(new_tx)
    
    # 3. Add to Blockchain Ledger
    blockchain_tx = Transaction(
        from_wallet=str(buyer_wallet.wallet_id), 
        to_wallet=str(seller_wallet.wallet_id), 
        amount=idea.price, 
        tx_type="idea_purchase",
        metadata={"idea_id": str(idea.idea_id), "buyer_id": str(current_user.id)}
    )
    
    tx_hash = invox_ledger.add_transaction(blockchain_tx)
    new_block = invox_ledger.mine_pending_transactions()
    
    # Update DB Transaction with Blockchain Hash
    new_tx.tx_hash = tx_hash
    # We do not save block_id to SQL to avoid Foreign Key mismatch 
    # since in-memory blockchain resets index on backend restart.
    db.commit()
    db.refresh(new_tx)
    
    # 4. Record the Purchase
    new_purchase = models.IdeaPurchase(
        idea_id=idea.idea_id,
        buyer_id=current_user.id,
        price=idea.price,
        tx_id=new_tx.id
    )
    db.add(new_purchase)
    db.commit()

    # Notify Buyer
    notify_token_purchase(current_user.email, idea.price, idea.title)
    # Notify Seller
    seller = db.query(models.User).filter(models.User.id == idea.owner_id).first()
    if seller:
        from app.utils.email import send_invox_email
        send_invox_email(
            seller.email, 
            "Earnings Alert: Asset Sold", 
            f"Your idea '{idea.title}' has been purchased for Ʉ {idea.price:.2f}. The tokens have been added to your ledger."
        )

    return {"message": "Purchase successful! You now have access.", "tx_hash": tx_hash}
