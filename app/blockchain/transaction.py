from typing import Dict, Any, Optional
import uuid
from time import time
import hashlib

class Transaction:
    def __init__(self, from_wallet: Optional[str], to_wallet: str, amount: float, tx_type: str = "transfer", metadata: dict = None):
        self.tx_id = str(uuid.uuid4())
        self.from_wallet = from_wallet
        self.to_wallet = to_wallet
        self.amount = amount
        self.tx_type = tx_type  # 'purchase', 'upload_reward', 'transfer'
        self.metadata = metadata or {}
        self.timestamp = time()
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tx_id": self.tx_id,
            "from_wallet": self.from_wallet,
            "to_wallet": self.to_wallet,
            "amount": self.amount,
            "tx_type": self.tx_type,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }
        
    def hash(self) -> str:
        import json
        tx_string = json.dumps(self.to_dict(), sort_keys=True).encode()
        return hashlib.sha256(tx_string).hexdigest()
