from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database.connection import get_db
from app.database import models
from app.schemas import idea_schema
from app.routes.dependencies import get_current_user
from app.blockchain.blockchain import invenio_ledger
from app.blockchain.transaction import Transaction
from app.utils.hashing import verify_password
from app.utils.email import (
    notify_token_purchase, 
    notify_bid_placed, 
    notify_bid_approved, 
    notify_bid_declined,
    notify_bid_cancelled,
    notify_counter_offer
)
from typing import List, Optional
from pydantic import BaseModel

class BuyRequest(BaseModel):
    password: str
    plan_months: Optional[int] = None

class BidResponsePayload(BaseModel):
    status: str # approved, rejected, countered
    password: str
    counter_price: Optional[float] = None

class BuyerBidResponsePayload(BaseModel):
    status: str # accepted, rejected, countered
    new_price: Optional[float] = None

router = APIRouter(prefix="/api/marketplace", tags=["Marketplace"])

# Existing routes...
@router.get("/ideas", response_model=List[idea_schema.IdeaResponse])
def get_all_ideas(category: str = None, q: str = None, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Show ideas that are public OR owned by the user
    query = db.query(models.Idea).filter(or_(models.Idea.is_public == True, models.Idea.owner_id == current_user.id))
    
    if category:
        query = query.filter(models.Idea.category == category)
    if q:
        search = f"%{q}%"
        query = query.filter(or_(models.Idea.title.ilike(search), models.Idea.keywords.ilike(search)))
        
    ideas_db = query.all()
    user_purchases = db.query(models.IdeaPurchase).filter(models.IdeaPurchase.buyer_id == current_user.id).all()
    
    ideas_response = []
    
    from datetime import datetime
    now = datetime.utcnow()
    
    for idea in ideas_db:
        # Check if they have an active license
        active_purchases = [p for p in user_purchases if p.idea_id == idea.idea_id]
        has_active_license = False
        for p in active_purchases:
            if not p.expiry_date or p.expiry_date > now:
                has_active_license = True
                break
        
        is_unlocked = (idea.owner_id == current_user.id) or has_active_license
        setattr(idea, "is_unlocked", is_unlocked)
        ideas_response.append(idea)

    return ideas_response

@router.get("/idea/{idea_id}", response_model=idea_schema.IdeaResponse)
def get_idea_detail(idea_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    idea = db.query(models.Idea).filter(models.Idea.idea_id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
        
    is_unlocked = (idea.owner_id == current_user.id)
    if not is_unlocked and user_purchase:
        from datetime import datetime
        now = datetime.utcnow()
        if not user_purchase.expiry_date or user_purchase.expiry_date > now:
            is_unlocked = True

    setattr(idea, "is_unlocked", is_unlocked)
    return idea

@router.post("/idea/{idea_id}/toggle-visibility")
def toggle_idea_visibility(idea_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    idea = db.query(models.Idea).filter(models.Idea.idea_id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    
    if idea.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can toggle marketplace visibility")
        
    idea.is_public = not idea.is_public
    db.commit()
    return {"is_public": idea.is_public, "message": "Visibility updated successfully"}

@router.get("/my-assets", response_model=List[idea_schema.IdeaResponse])
def get_my_assets(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Get ideas currently owned by the user
    my_ideas = db.query(models.Idea).filter(models.Idea.owner_id == current_user.id).all()
    for idea in my_ideas:
        setattr(idea, "is_unlocked", True) # Obviously owned
    return my_ideas

@router.post("/buy/{idea_id}")
def buy_idea(idea_id: str, payload: BuyRequest, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid Account PIN/Password")

    idea = db.query(models.Idea).filter(models.Idea.idea_id == idea_id).first()
    if not idea or idea.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="Invalid request")

    price = idea.price
    if payload.plan_months == 1:
        price = idea.plan_1m_price
    elif payload.plan_months == 3:
        price = idea.plan_3m_price
    elif payload.plan_months == 6:
        price = idea.plan_6m_price

    if price is None:
        raise HTTPException(status_code=400, detail="Invalid plan selected or plan not available")

    buyer_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    seller_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == idea.owner_id).first()
    
    if buyer_wallet.balance < price:
        raise HTTPException(status_code=400, detail="Insufficient INVENIO token balance")

    fee_amount = price * 0.02
    seller_amount = price - fee_amount

    buyer_wallet.balance -= price
    seller_wallet.balance += seller_amount
    
    new_tx = models.Transaction(from_wallet=buyer_wallet.wallet_id, to_wallet=seller_wallet.wallet_id, amount=seller_amount, tx_hash="pending")
    db.add(new_tx)

    fee_tx = models.Transaction(from_wallet=buyer_wallet.wallet_id, to_wallet=None, amount=fee_amount, tx_hash="fee_pending")
    db.add(fee_tx)
    
    blockchain_tx = Transaction(from_wallet=str(buyer_wallet.wallet_id), to_wallet=str(seller_wallet.wallet_id), amount=price, tx_type="idea_license", metadata={"idea_id": str(idea.idea_id), "plan_months": payload.plan_months})
    tx_hash = invenio_ledger.add_transaction(blockchain_tx)
    invenio_ledger.mine_pending_transactions()
    
    new_tx.tx_hash = tx_hash
    fee_tx.tx_hash = tx_hash + "-fee"

    from datetime import datetime, timedelta
    expiry_date = None
    if payload.plan_months:
        expiry_date = datetime.utcnow() + timedelta(days=payload.plan_months * 30)

    new_purchase = models.IdeaPurchase(
        idea_id=idea.idea_id, 
        buyer_id=current_user.id, 
        price=price, 
        tx_id=new_tx.id,
        plan_duration_months=payload.plan_months,
        expiry_date=expiry_date
    )
    db.add(new_purchase)
    db.commit()

    notify_token_purchase(current_user.email, idea.price, idea.title)
    return {"message": "Purchase successful", "tx_hash": tx_hash}

@router.post("/bid")
def place_ownership_bid(payload: idea_schema.OwnershipBidCreate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    idea = db.query(models.Idea).filter(models.Idea.idea_id == payload.idea_id).first()
    if not idea or idea.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="Invalid bidding target")

    from datetime import datetime
    now = datetime.utcnow()
    # Check if this idea has any active licenses
    active_licenses = db.query(models.IdeaPurchase).filter(
        models.IdeaPurchase.idea_id == payload.idea_id,
        or_(models.IdeaPurchase.expiry_date == None, models.IdeaPurchase.expiry_date > now)
    ).count()
    if active_licenses > 0:
        raise HTTPException(status_code=400, detail="This idea has active licenses and cannot be sold for ownership right now.")

    # LOCK TOKENS IMMEDIATELY
    buyer_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    if buyer_wallet.balance < payload.price:
        raise HTTPException(status_code=400, detail="Insufficient balance to lock for bid")

    buyer_wallet.balance -= payload.price
    
    new_bid = models.OwnershipBid(
        idea_id=payload.idea_id,
        bidder_id=current_user.id,
        price=payload.price, # Original Bid
        last_action_by="buyer",
        status="pending"
    )
    db.add(new_bid)
    db.commit()
    db.refresh(new_bid)
    
    notify_bid_placed(idea.owner.email, idea.title, current_user.name, payload.price)
    return new_bid

@router.get("/bids/received", response_model=List[idea_schema.OwnershipBidResponse])
def get_received_bids(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Show bids where current user is the owner
    return db.query(models.OwnershipBid).join(models.Idea).filter(
        models.Idea.owner_id == current_user.id,
        models.OwnershipBid.status.in_(["pending", "countered"])
    ).all()

@router.get("/bids/sent", response_model=List[idea_schema.OwnershipBidResponse])
def get_sent_bids(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(models.OwnershipBid).filter(models.OwnershipBid.bidder_id == current_user.id).all()

@router.post("/bid/{bid_id}/cancel")
def cancel_ownership_bid(bid_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    bid = db.query(models.OwnershipBid).filter(models.OwnershipBid.id == bid_id, models.OwnershipBid.bidder_id == current_user.id).first()
    if not bid or bid.status not in ["pending", "countered"]:
        raise HTTPException(status_code=400, detail="Bid cannot be cancelled")
    
    # REFUND TOKENS
    buyer_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    buyer_wallet.balance += bid.price
    
    bid.status = "cancelled"
    db.commit()
    
    notify_bid_cancelled(bid.idea.owner.email, bid.idea.title, current_user.name)
    return {"message": "Bid cancelled and tokens refunded"}

@router.post("/bid/{bid_id}/respond")
def respond_to_bid(bid_id: str, payload: BidResponsePayload, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid Account PIN")

    bid = db.query(models.OwnershipBid).filter(models.OwnershipBid.id == bid_id).first()
    if not bid or bid.idea.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    if payload.status == "rejected":
        # REFUND BUYER
        buyer_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == bid.bidder_id).first()
        buyer_wallet.balance += bid.price
        bid.status = "rejected"
        db.commit()
        notify_bid_declined(bid.bidder.email, bid.idea.title)
        return {"message": "Bid rejected and tokens refunded to buyer"}

    if payload.status == "countered":
        if not payload.counter_price or payload.counter_price <= 0:
            raise HTTPException(status_code=400, detail="Invalid counter price")
        bid.counter_price = payload.counter_price
        bid.status = "countered"
        bid.last_action_by = "seller"
        db.commit()
        notify_counter_offer(bid.bidder.email, bid.idea.title, bid.counter_price, current_user.name)
        return {"message": "Counter offer sent"}

    if payload.status == "approved":
        # FINAL TRANSFER (Escrowed tokens only)
        # We need to lock the idea record for pessimistic concurrency
        idea = db.query(models.Idea).with_for_update().filter(models.Idea.idea_id == bid.idea_id).first()
        if idea.owner_id != current_user.id:
            raise HTTPException(status_code=400, detail="Asset already transferred or unauthorized")

        seller_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
        seller_wallet.balance += bid.price

        # Record Ledger
        new_tx = models.Transaction(from_wallet=None, to_wallet=seller_wallet.wallet_id, amount=bid.price, tx_hash="escrow_settle")
        db.add(new_tx)

        blockchain_tx = Transaction(from_wallet="Escrow", to_wallet=str(seller_wallet.wallet_id), amount=bid.price, tx_type="ownership_transfer_final", metadata={"idea_id": str(idea.idea_id)})
        tx_hash = invenio_ledger.add_transaction(blockchain_tx)
        invenio_ledger.mine_pending_transactions()
        
        idea.owner_id = bid.bidder_id
        bid.status = "completed"

        # Record record in purchases
        new_purchase = models.IdeaPurchase(idea_id=idea.idea_id, buyer_id=bid.bidder_id, price=bid.price, tx_id=new_tx.id)
        db.add(new_purchase)
        
        db.commit()
        
        notify_bid_approved(bid.bidder.email, idea.title, bid.price)
        return {"message": "Ownership transferred successfully"}

@router.post("/bid/{bid_id}/buyer-respond")
def buyer_respond_to_bid(bid_id: str, payload: BuyerBidResponsePayload, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    bid = db.query(models.OwnershipBid).filter(models.OwnershipBid.id == bid_id, models.OwnershipBid.bidder_id == current_user.id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")

    if payload.status == "rejected":
        # Refund current escrow
        wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
        wallet.balance += bid.price
        bid.status = "cancelled"
        db.commit()
        return {"message": "Offer withdrawn and tokens refunded"}

    if payload.status == "accepted":
        # Buyer accepts seller's counter_price
        if not bid.counter_price:
             raise HTTPException(status_code=400, detail="No counter offer to accept")
        
        diff = bid.counter_price - bid.price
        wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
        if wallet.balance < diff:
             raise HTTPException(status_code=400, detail=f"Insufficient balance for diff: {diff}")
        
        # PESSIMISTIC LOCK Asset
        idea = db.query(models.Idea).with_for_update().filter(models.Idea.idea_id == bid.idea_id).first()
        seller_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == idea.owner_id).first()

        wallet.balance -= diff
        seller_wallet.balance += bid.counter_price # full amount (escrowed + diff)
        
        idea.owner_id = current_user.id
        bid.status = "completed"

        new_tx = models.Transaction(from_wallet=wallet.wallet_id, to_wallet=seller_wallet.wallet_id, amount=diff, tx_hash="escrow_diff_settle")
        db.add(new_tx)
        db.flush()

        # Record record in purchases
        new_purchase = models.IdeaPurchase(idea_id=idea.idea_id, buyer_id=current_user.id, price=bid.counter_price, tx_id=new_tx.id)
        db.add(new_purchase)

        db.commit()

        notify_bid_approved(current_user.email, idea.title, bid.counter_price)
        return {"message": "Success! You are now the legal owner"}

    if payload.status == "countered":
        # Buyer countered again
        diff = payload.new_price - bid.price
        wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
        if wallet.balance < diff:
             raise HTTPException(status_code=400, detail="Insufficient balance for new offer")
        
        wallet.balance -= diff
        bid.price = payload.new_price
        bid.status = "pending"
        bid.last_action_by = "buyer"
        db.commit()
        notify_counter_offer(bid.idea.owner.email, bid.idea.title, bid.price, current_user.name)
        return {"message": "New offer submitted"}

@router.get("/idea/{idea_id}/licenses", response_model=List[idea_schema.LicenseResponse])
def get_idea_licenses(idea_id: str, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    idea = db.query(models.Idea).filter(models.Idea.idea_id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
        
    if idea.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the owner can view license records")
        
    licenses = db.query(models.IdeaPurchase).filter(models.IdeaPurchase.idea_id == idea_id).all()
    return licenses
