from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from app.schemas.user_schema import UserResponse

class IdeaCreate(BaseModel):
    title: str
    problem_statement: str
    research_info: str
    solution: str
    keywords: str
    category: str
    sale_type: Optional[str] = "both"
    price: float
    plan_1m_price: Optional[float] = None
    plan_3m_price: Optional[float] = None
    plan_6m_price: Optional[float] = None

class IdeaPricingUpdate(BaseModel):
    sale_type: Optional[str] = None
    price: Optional[float] = None
    plan_1m_price: Optional[float] = None
    plan_3m_price: Optional[float] = None
    plan_6m_price: Optional[float] = None

class IdeaResponse(BaseModel):
    idea_id: UUID
    title: str
    problem_statement: str
    research_info: str
    solution: str
    keywords: str
    category: str
    sale_type: Optional[str] = "both"
    owner_id: UUID
    price: float
    ipfs_hash: Optional[str] = None
    created_at: datetime
    is_unlocked: Optional[bool] = False
    is_public: bool = True
    plan_1m_price: Optional[float] = None
    plan_3m_price: Optional[float] = None
    plan_6m_price: Optional[float] = None
    owner: Optional[UserResponse] = None

class LicenseResponse(BaseModel):
    id: UUID
    idea_id: UUID
    buyer_id: UUID
    price: float
    plan_duration_months: Optional[int] = None
    expiry_date: Optional[datetime] = None
    created_at: datetime
    buyer: Optional[UserResponse] = None

    class Config:
        from_attributes = True

    class Config:
        from_attributes = True
        
class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    similarity_score: float
    message: str
    similar_idea_id: Optional[UUID] = None

class OwnershipBidBase(BaseModel):
    idea_id: UUID
    price: float

class OwnershipBidCreate(OwnershipBidBase):
    pass

class OwnershipBidResponse(OwnershipBidBase):
    id: UUID
    bidder_id: UUID
    status: str
    counter_price: Optional[float] = None
    last_action_by: Optional[str] = "buyer"
    created_at: datetime
    bidder: Optional[UserResponse] = None
    idea: Optional[IdeaResponse] = None

    class Config:
        from_attributes = True
