from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from uuid import UUID

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class PasswordUpdate(BaseModel):
    old_password: str
    new_password: str

class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    wallet_id: Optional[UUID] = None
    is_email_public: bool = False
    is_admin: bool = False
    balance: float = 0.0
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    is_admin: bool = False
    admin_path: Optional[str] = None
    
class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None
