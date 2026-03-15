from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database import models
from app.routes.dependencies import get_current_user
from app.utils.email import notify_query_resolved, notify_withdrawal_processed
from typing import List
from pydantic import BaseModel
from sqlalchemy import func
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# Helper to ensure user is admin
def verify_admin(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# 1. User Management
@router.get("/users", dependencies=[Depends(verify_admin)])
def get_all_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

@router.delete("/users/{user_id}", dependencies=[Depends(verify_admin)])
def delete_user(user_id: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}

class TokenModification(BaseModel):
    amount: float
    reason: str = "Admin adjustment"

@router.post("/users/{user_id}/modify-tokens", dependencies=[Depends(verify_admin)])
def modify_user_tokens(user_id: str, payload: TokenModification, db: Session = Depends(get_db)):
    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == user_id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    wallet.balance += payload.amount
    if wallet.balance < 0:
        wallet.balance = 0
        
    # Log it as a transaction
    new_tx = models.Transaction(
        from_wallet=None,
        to_wallet=wallet.wallet_id,
        amount=payload.amount,
        tx_hash=f"admin_mod_{str(datetime.utcnow().timestamp())}"
    )
    db.add(new_tx)
    db.commit()
    return {"message": "Balance updated", "new_balance": wallet.balance}

# 2. Post (Idea) Management
@router.get("/ideas", dependencies=[Depends(verify_admin)])
def get_all_ideas(db: Session = Depends(get_db)):
    ideas = db.query(models.Idea).all()
    # Eagerly load owners to show in modal
    result = []
    for i in ideas:
        owner = db.query(models.User).filter(models.User.id == i.owner_id).first()
        result.append({
            "idea_id": str(i.idea_id),
            "title": i.title,
            "category": i.category,
            "price": i.price,
            "created_at": i.created_at,
            "owner_name": owner.name if owner else "Unknown",
            "owner_email": owner.email if owner else "Unknown",
            "problem_statement": i.problem_statement,
            "solution": i.solution
        })
    return result

@router.delete("/ideas/{idea_id}", dependencies=[Depends(verify_admin)])
def delete_idea(idea_id: str, db: Session = Depends(get_db)):
    idea = db.query(models.Idea).filter(models.Idea.idea_id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    db.delete(idea)
    db.commit()
    return {"message": "Idea deleted"}

# 3. Problem Statement Management
@router.get("/problems", dependencies=[Depends(verify_admin)])
def get_all_problems(db: Session = Depends(get_db)):
    problems = db.query(models.Problem).all()
    result = []
    for p in problems:
        author = db.query(models.User).filter(models.User.id == p.user_id).first()
        result.append({
            "id": str(p.id),
            "title": p.title,
            "category": p.category,
            "created_at": p.created_at,
            "author_name": author.name if author else "Unknown",
            "author_email": author.email if author else "Unknown",
            "description": p.description
        })
    return result

@router.delete("/problems/{problem_id}", dependencies=[Depends(verify_admin)])
def delete_problem(problem_id: str, db: Session = Depends(get_db)):
    problem = db.query(models.Problem).filter(models.Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    db.delete(problem)
    db.commit()
    return {"message": "Problem deleted"}

# 4. Withdrawal Request Management
@router.get("/withdrawals", dependencies=[Depends(verify_admin)])
def get_all_withdrawals(db: Session = Depends(get_db)):
    withdrawals = db.query(models.WithdrawalRequest).all()
    result = []
    for w in withdrawals:
        user = db.query(models.User).filter(models.User.id == w.user_id).first()
        result.append({
            "id": str(w.id),
            "amount": w.amount,
            "payment_method": w.payment_method,
            "payment_details": w.payment_details,
            "status": w.status,
            "created_at": w.created_at,
            "user_name": user.name if user else "Unknown",
            "user_email": user.email if user else "Unknown"
        })
    return result

class WithdrawalStatusUpdate(BaseModel):
    status: str # approved, rejected
    admin_note: str = None

@router.post("/withdrawals/{request_id}/status", dependencies=[Depends(verify_admin)])
def update_withdrawal_status(request_id: str, payload: WithdrawalStatusUpdate, db: Session = Depends(get_db)):
    req = db.query(models.WithdrawalRequest).filter(models.WithdrawalRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if req.status != "pending":
         raise HTTPException(status_code=400, detail="Request already processed")

    user = db.query(models.User).filter(models.User.id == req.user_id).first()
    
    if payload.status == "rejected":
        # Refund tokens back to balance since they were locked (deducted) on request
        wallet = db.query(models.Wallet).filter(models.Wallet.user_id == req.user_id).first()
        wallet.balance += req.amount

    req.status = payload.status
    req.admin_note = payload.admin_note
    db.commit()

    # Send Notification Email
    if user:
        notify_withdrawal_processed(user.email, req.amount, payload.status, payload.admin_note)

    return {"message": f"Withdrawal {payload.status}"}

# 5. User Query Management
@router.get("/queries", dependencies=[Depends(verify_admin)])
def get_all_queries(db: Session = Depends(get_db)):
    queries = db.query(models.UserQuery).all()
    result = []
    for q in queries:
        user = db.query(models.User).filter(models.User.id == q.user_id).first()
        result.append({
            "id": str(q.id),
            "subject": q.subject,
            "message": q.message,
            "is_resolved": q.is_resolved,
            "created_at": q.created_at,
            "admin_note": q.admin_note,
            "user_name": user.name if user else "Unknown",
            "user_email": user.email if user else "Unknown"
        })
    return result

class ResolveQueryPayload(BaseModel):
    admin_note: str = ""

@router.post("/queries/{query_id}/resolve", dependencies=[Depends(verify_admin)])
def resolve_query(query_id: str, payload: ResolveQueryPayload, db: Session = Depends(get_db)):
    query = db.query(models.UserQuery).filter(models.UserQuery.id == query_id).first()
    if not query:
        raise HTTPException(status_code=404, detail="Query not found")
    
    query.is_resolved = True
    query.admin_note = payload.admin_note
    user = db.query(models.User).filter(models.User.id == query.user_id).first()
    db.commit()

    # Send Notification Email
    if user:
        notify_query_resolved(user.email, str(query.id), payload.admin_note)

    return {"message": "Query marked as resolved"}

# 6. Payment System Management (Overview/Analytics)
@router.get("/payments/stats", dependencies=[Depends(verify_admin)])
def get_payment_stats(db: Session = Depends(get_db)):
    # 1. Fixed Sum Calculation: Total tokens purchased (fiat inflow)
    total_tokens_bought = db.query(func.sum(models.Transaction.amount)).filter(models.Transaction.from_wallet == None).scalar() or 0
    
    # 2. Total Withdrawals (outflow)
    total_withdrawn = db.query(func.sum(models.WithdrawalRequest.amount)).filter(models.WithdrawalRequest.status == "approved").scalar() or 0

    # 3. User Stats
    total_users = db.query(models.User).count()
    # "Active" defined as users who have a balance or have made a transaction
    active_users = db.query(models.Wallet).filter(models.Wallet.balance > 0).count()

    # 4. Daily Purchase Trend (Last 7 Days)
    daily_purchases = []
    for i in range(7):
        date = (datetime.utcnow() - timedelta(days=i)).date()
        daily_sum = db.query(func.sum(models.Transaction.amount)).filter(
            models.Transaction.from_wallet == None,
            func.date(models.Transaction.created_at) == date
        ).scalar() or 0
        daily_purchases.append({"date": date.strftime("%Y-%m-%d"), "amount": daily_sum})
    
    daily_purchases.reverse()

    return {
        "total_tokens_issued": float(total_tokens_bought),
        "total_withdrawn": float(total_withdrawn),
        "active_users": active_users,
        "total_users": total_users,
        "total_ideas": db.query(models.Idea).count(),
        "daily_trends": daily_purchases,
        "recent_withdrawals": db.query(models.WithdrawalRequest).order_by(models.WithdrawalRequest.created_at.desc()).limit(5).all(),
        "recent_queries": db.query(models.UserQuery).order_by(models.UserQuery.created_at.desc()).limit(5).all()
    }

# 7. System Configuration
@router.get("/settings", dependencies=[Depends(verify_admin)])
def get_system_settings(db: Session = Depends(get_db)):
    settings_list = db.query(models.SystemSetting).all()
    # Ensure test_mode exists and default to true for this deployment
    test_mode = db.query(models.SystemSetting).filter(models.SystemSetting.key == "test_mode").first()
    if not test_mode:
        test_mode = models.SystemSetting(key="test_mode", value="true", description="Allow users to claim free tokens and bypass payments for testing")
        db.add(test_mode)
        db.commit()
        db.refresh(test_mode)
        settings_list = db.query(models.SystemSetting).all()
    
    return {s.key: s.value == "true" if s.value in ["true", "false"] else s.value for s in settings_list}

class UpdateSettingPayload(BaseModel):
    key: str
    value: str

@router.post("/settings", dependencies=[Depends(verify_admin)])
def update_system_setting(payload: UpdateSettingPayload, db: Session = Depends(get_db)):
    setting = db.query(models.SystemSetting).filter(models.SystemSetting.key == payload.key).first()
    if not setting:
        setting = models.SystemSetting(key=payload.key)
        db.add(setting)
    
    setting.value = payload.value
    db.commit()
    return {"message": f"Setting '{payload.key}' updated to {payload.value}"}
