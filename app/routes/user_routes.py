from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import models
from app.schemas import user_schema
from app.utils.email import notify_query_submitted, notify_withdrawal_requested
from app.routes.dependencies import get_current_user
from app.blockchain.blockchain import invox_ledger
from app.blockchain.transaction import Transaction
from app.database.connection import get_db
from pydantic import BaseModel, Field
from typing import List

router = APIRouter(prefix="/api/users", tags=["Users"])

class ToggleEmailPayload(BaseModel):
    is_public: bool

@router.get("/me/dashboard")
def get_user_dashboard_stats(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    ideas_count = db.query(models.Idea).filter(models.Idea.owner_id == current_user.id).count()
    purchases_count = db.query(models.IdeaPurchase).filter(models.IdeaPurchase.buyer_id == current_user.id).count()
    
    return {
        "ideas_count": ideas_count,
        "purchased_assets_count": purchases_count
    }

@router.get("/{user_id}")
def get_user_profile(user_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    followers = db.query(models.UserFollow).filter(models.UserFollow.following_id == user_id).count()
    following = db.query(models.UserFollow).filter(models.UserFollow.follower_id == user_id).count()
    
    is_following = db.query(models.UserFollow).filter(
        models.UserFollow.follower_id == current_user.id,
        models.UserFollow.following_id == user_id
    ).first() is not None
    
    # Check if email view is purchased
    has_purchased_email = False
    if not user.is_email_public and user_id != str(current_user.id):
        purchase = db.query(models.EmailViewPurchase).filter(
            models.EmailViewPurchase.viewer_id == current_user.id,
            models.EmailViewPurchase.creator_id == user_id
        ).first()
        has_purchased_email = purchase is not None
    
    ideas = db.query(models.Idea).filter(models.Idea.owner_id == user_id).all()
    
    email_to_show = user.email if (user.is_email_public or has_purchased_email or user_id == str(current_user.id)) else None
    
    return {
        "id": user.id,
        "name": user.name,
        "email": email_to_show,
        "is_email_public": user.is_email_public,
        "followers_count": followers,
        "following_count": following,
        "is_following": is_following,
        "ideas": [{"idea_id": i.idea_id, "title": i.title, "category": i.category} for i in ideas],
        "has_purchased_email": has_purchased_email
    }

@router.post("/{user_id}/follow")
def toggle_follow(user_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user_id == str(current_user.id):
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
        
    existing = db.query(models.UserFollow).filter(
        models.UserFollow.follower_id == current_user.id,
        models.UserFollow.following_id == user_id
    ).first()
    
    if existing:
        db.delete(existing)
        db.commit()
        return {"message": "Unfollowed", "is_following": False}
    else:
        new_follow = models.UserFollow(follower_id=current_user.id, following_id=user_id)
        db.add(new_follow)
        db.commit()
        return {"message": "Followed", "is_following": True}

@router.post("/me/toggle-email")
def toggle_email_visibility(payload: ToggleEmailPayload, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # If the user is trying to make it public for the first time, charge them 5 tokens.
    if payload.is_public and not current_user.is_email_public:
        wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
        price = 5.0
        if wallet.balance < price:
            raise HTTPException(status_code=400, detail="Making email public costs 5 Ʉ. Insufficient token balance.")
        
        wallet.balance -= price
        
        new_tx = models.Transaction(
            from_wallet=wallet.wallet_id,
            to_wallet=None,
            amount=price,
            tx_hash="pending"
        )
        db.add(new_tx)
        
        blockchain_tx = Transaction(
            from_wallet=str(wallet.wallet_id), 
            to_wallet="System", 
            amount=price, 
            tx_type="email_public_fee",
            metadata={"user_id": str(current_user.id)}
        )
        tx_hash = invox_ledger.add_transaction(blockchain_tx)
        invox_ledger.mine_pending_transactions()
        
        new_tx.tx_hash = tx_hash
        db.commit()
        
    current_user.is_email_public = payload.is_public
    db.commit()
    return {"message": "Visibility updated", "is_email_public": current_user.is_email_public}

@router.post("/{user_id}/reveal-email")
def reveal_email(user_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    creator = db.query(models.User).filter(models.User.id == user_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="User not found")
        
    if creator.is_email_public:
        return {"message": "Already public", "email": creator.email}
        
    existing_purchase = db.query(models.EmailViewPurchase).filter(
        models.EmailViewPurchase.viewer_id == current_user.id,
        models.EmailViewPurchase.creator_id == user_id
    ).first()
    
    if existing_purchase:
        return {"message": "Already purchased", "email": creator.email}
        
    viewer_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    creator_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == creator.id).first()
    
    price = 2.0  # 2 Invox tokens to reveal
    if viewer_wallet.balance < price:
        raise HTTPException(status_code=400, detail=f"Cost is {price} Ʉ. Insufficient token balance to reveal email.")
        
    viewer_wallet.balance -= price
    creator_wallet.balance += price
    
    new_tx = models.Transaction(
        from_wallet=viewer_wallet.wallet_id,
        to_wallet=creator_wallet.wallet_id,
        amount=price,
        tx_hash="pending"
    )
    db.add(new_tx)
    
    blockchain_tx = Transaction(
        from_wallet=str(viewer_wallet.wallet_id), 
        to_wallet=str(creator_wallet.wallet_id), 
        amount=price, 
        tx_type="email_reveal",
        metadata={"creator_id": user_id, "viewer_id": str(current_user.id)}
    )
    
    tx_hash = invox_ledger.add_transaction(blockchain_tx)
    invox_ledger.mine_pending_transactions()
    
    new_tx.tx_hash = tx_hash
    db.commit()
    db.refresh(new_tx)
    
    purchase = models.EmailViewPurchase(
        viewer_id=current_user.id,
        creator_id=creator.id,
        price=price,
        tx_id=new_tx.id
    )
    db.add(purchase)
    db.commit()
    
    return {"message": "Email revealed", "email": creator.email, "tx_hash": tx_hash}

@router.get("/me/purchases")
def get_my_purchases(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    purchases = db.query(models.IdeaPurchase).filter(models.IdeaPurchase.buyer_id == current_user.id).all()
    
    # We want to show the idea details as well
    result = []
    for p in purchases:
        idea = db.query(models.Idea).filter(models.Idea.idea_id == p.idea_id).first()
        tx = db.query(models.Transaction).filter(models.Transaction.id == p.tx_id).first()
        result.append({
            "purchase_id": p.id,
            "idea_id": p.idea_id,
            "title": idea.title if idea else "Unknown Idea",
            "price": p.price,
            "tx_hash": tx.tx_hash if tx else "N/A",
            "date": p.created_at
        })
    
    # Dashboard stats at the top
    # 1. Total tokens purchased (via Fiat)
    total_purchased = db.query(models.Transaction).filter(
        models.Transaction.to_wallet == current_user.wallet_id,
        models.Transaction.from_wallet == None
    ).all()
    # Note: Filter further if you have other system rewards. For now, from_wallet=None is fiat_purchase in wallet_routes.
    
    total_tokens_bought = sum(tx.amount for tx in total_purchased)
    
    # 2. Total withdrawals (done or pending)
    withdrawals = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.user_id == current_user.id).all()
    total_withdrawals = sum(w.amount for w in withdrawals if w.status == "approved")
    
    return {
        "purchases": result,
        "stats": {
            "total_tokens_purchased": total_tokens_bought,
            "total_withdrawn": total_withdrawals,
            "current_balance": db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first().balance
        }
    }

class WithdrawalCreate(BaseModel):
    amount: float = Field(gt=0)
    payment_method: str # 'UPI' or 'Bank'
    payment_details: str

@router.post("/me/withdraw")
def request_withdrawal(payload: WithdrawalCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check if Test Mode is ON
    test_mode = db.query(models.SystemSetting).filter(models.SystemSetting.key == "test_mode").first()
    if test_mode and test_mode.value == "true":
        raise HTTPException(status_code=403, detail="Withdrawals are disabled while Platform Test Mode is active.")

    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    if wallet.balance < payload.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance for withdrawal")
    
    # Check for pending requests
    pending = db.query(models.WithdrawalRequest).filter(
        models.WithdrawalRequest.user_id == current_user.id,
        models.WithdrawalRequest.status == "pending"
    ).first()
    if pending:
        raise HTTPException(status_code=400, detail="You already have a pending withdrawal request")

    new_request = models.WithdrawalRequest(
        user_id=current_user.id,
        amount=payload.amount,
        payment_method=payload.payment_method,
        payment_details=payload.payment_details
    )
    
    # LOCK TOKENS: Deduct from balance immediately on request
    wallet.balance -= payload.amount
    
    db.add(new_request)
    db.commit()

    # Notify User via Email
    notify_withdrawal_requested(current_user.email, payload.amount, payload.payment_method)

    return {"message": "Withdrawal request submitted. Tokens are now locked for verification."}

class QueryCreate(BaseModel):
    subject: str
    message: str

@router.post("/me/queries")
def submit_query(payload: QueryCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_query = models.UserQuery(
        user_id=current_user.id,
        subject=payload.subject,
        message=payload.message
    )
    db.add(new_query)
    db.commit()
    db.refresh(new_query)

    # Notify User via Email with Ticket ID
    notify_query_submitted(current_user.email, str(new_query.id), payload.subject, payload.message)

    return {"message": "Query submitted successfully. Check your email for Ticket ID.", "ticket_id": str(new_query.id)}

@router.get("/me/withdrawals")
def get_my_withdrawals(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.user_id == current_user.id).all()
