from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class TransactionResponse(BaseModel):
    id: UUID
    from_wallet: Optional[UUID] = None
    to_wallet: UUID
    amount: float
    tx_hash: Optional[str] = None
    block_id: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
