from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class WalletResponse(BaseModel):
    wallet_id: UUID
    user_id: UUID
    balance: float
    created_at: datetime
    
    class Config:
        from_attributes = True

class BuyTokensRequest(BaseModel):
    amount: float
