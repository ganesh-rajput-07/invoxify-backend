from typing import List, Dict, Any, Optional
from app.blockchain.block import Block
from app.blockchain.transaction import Transaction

class Blockchain:
    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[Dict[str, Any]] = []
        self._create_genesis_block()

    def _create_genesis_block(self):
        """Create the first block in the chain."""
        genesis_block = Block(0, [], "0" * 64)
        self.chain.append(genesis_block)

    def get_latest_block(self) -> Block:
        """Return the most recent block."""
        return self.chain[-1]

    def add_transaction(self, transaction: Transaction) -> str:
        """Add a transaction to the pending list."""
        self.pending_transactions.append(transaction.to_dict())
        return transaction.hash()

    def mine_pending_transactions(self) -> Optional[Block]:
        """Create a new block from pending transactions and mine it."""
        if not self.pending_transactions:
            return None

        last_block = self.get_latest_block()
        
        # In a real blockchain, we'd do Proof of Work here.
        # For our custom internal DB-backed ledger, we just create the block.
        new_block = Block(last_block.index + 1, self.pending_transactions, last_block.hash)
        
        self.chain.append(new_block)
        
        # Reset pending
        self.pending_transactions = []
        
        return new_block

    def validate_chain(self) -> bool:
        """Verify the integrity of the blockchain."""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i-1]
            
            # Check block hash
            if current_block.hash != current_block.calculate_hash():
                return False
                
            # Check hash linking
            if current_block.previous_hash != previous_block.hash:
                return False
                
        return True

# Instantiate a global internal ledger
invenio_ledger = Blockchain()
