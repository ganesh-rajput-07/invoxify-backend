from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.database.connection import get_db
from app.database import models
from app.schemas import user_schema
from app.utils.hashing import get_password_hash, verify_password
from app.services.auth_service import create_access_token
from app.routes.dependencies import get_current_user
from app.utils.email import send_password_reset_email
from pydantic import BaseModel, EmailStr
import uuid
import secrets
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register", response_model=user_schema.UserResponse)
def register(user: user_schema.UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = get_password_hash(user.password)
    new_user = models.User(
        name=user.name,
        email=user.email,
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create associated wallet
    new_wallet = models.Wallet(user_id=new_user.id)
    db.add(new_wallet)
    db.commit()
    db.refresh(new_wallet)
    
    # Update user with wallet ID
    new_user.wallet_id = new_wallet.wallet_id
    db.commit()
    db.refresh(new_user)

    return new_user

@router.post("/login", response_model=user_schema.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(data={"sub": user.email, "user_id": str(user.id)})
    
    admin_path = None
    if user.is_admin:
        # Generate a semi-dynamic secret path for this session
        admin_path = f"admin-{str(uuid.uuid4())[:8]}"
        
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "is_admin": user.is_admin,
        "admin_path": admin_path
    }

@router.get("/me", response_model=user_schema.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    current_user.balance = wallet.balance if wallet else 0.0
    return current_user

@router.post("/update-password")
def update_password(payload: user_schema.PasswordUpdate, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect old password")
        
    current_user.password_hash = get_password_hash(payload.new_password)
    db.commit()
    
    return {"message": "Password updated successfully"}

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

@router.post("/forgot-password")
def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user:
        return {"message": "If an account exists with this email, a reset link has been sent."}
    
    # Generate token
    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_expiry = datetime.utcnow() + timedelta(hours=1)
    db.commit()
    
    # Get origin from request headers to make link dynamic
    origin = request.headers.get("origin") or "http://localhost:3000"
    
    # Send actual email (or mock print if credentials missing)
    send_password_reset_email(user.email, token, origin)
    
    return {"message": "If an account exists with this email, a reset link has been sent.", "debug_token": token}

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    if payload.new_password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
        
    user = db.query(models.User).filter(
        models.User.reset_token == payload.token,
        models.User.reset_expiry > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        
    user.password_hash = get_password_hash(payload.new_password)
    user.reset_token = None
    user.reset_expiry = None
    db.commit()
    
    return {"message": "Password reset successfully"}
