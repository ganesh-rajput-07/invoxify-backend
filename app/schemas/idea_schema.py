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
    price: float

class IdeaResponse(BaseModel):
    idea_id: UUID
    title: str
    problem_statement: str
    research_info: str
    solution: str
    keywords: str
    category: str
    owner_id: UUID
    price: float
    ipfs_hash: Optional[str] = None
    created_at: datetime
    is_unlocked: Optional[bool] = False
    owner: Optional[UserResponse] = None

    class Config:
        from_attributes = True
        
class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    similarity_score: float
    message: str
    similar_idea_id: Optional[UUID] = None
