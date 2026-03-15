from pydantic import BaseModel, UUID4
from typing import Optional, List
from datetime import datetime
from app.schemas.user_schema import UserResponse
from app.schemas.idea_schema import IdeaResponse

class ProblemCommentCreate(BaseModel):
    content: str
    parent_id: Optional[UUID4] = None

class ProblemCommentResponse(BaseModel):
    id: UUID4
    problem_id: UUID4
    user_id: UUID4
    content: str
    parent_id: Optional[UUID4] = None
    created_at: datetime
    author: UserResponse
    replies: Optional[List['ProblemCommentResponse']] = []

    class Config:
        from_attributes = True

ProblemCommentResponse.update_forward_refs()

class ProblemCreate(BaseModel):
    title: str
    description: str
    category: str

class ProblemResponse(BaseModel):
    id: UUID4
    title: str
    description: str
    category: str
    user_id: UUID4
    created_at: datetime
    author: UserResponse
    comments_count: Optional[int] = 0
    saves_count: Optional[int] = 0
    is_saved: Optional[bool] = False
    
    # We might want comments directly on detail view
    comments: Optional[List[ProblemCommentResponse]] = []
    proposed_solutions: Optional[List[IdeaResponse]] = []

    class Config:
        from_attributes = True
