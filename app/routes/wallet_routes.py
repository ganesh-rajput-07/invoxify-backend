from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.database import models
from app.schemas import wallet_schema
from app.routes.dependencies import get_current_user
from app.blockchain.blockchain import invenio_ledger
from app.blockchain.transaction import Transaction

router = APIRouter(prefix="/api/wallet", tags=["Wallet"])

@router.get("/", response_model=wallet_schema.WalletResponse)
def get_wallet(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet

import razorpay
from app.config.settings import settings

razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@router.post("/create-razorpay-order")
def create_razorpay_order(payload: dict, current_user: models.User = Depends(get_current_user)):
    amount = float(payload.get("amount", 0))
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be > 0")

    # Assuming 1 INVENIO = 1 INR (or USD depending on currency config)
    # Razorpay expects amount in paise (multiply by 100)
    order_amount = int(amount * 100)
    order_currency = "INR"

    order_receipt = f"rcpt_{str(current_user.id)[:30]}"
    notes = {"user_id": str(current_user.id), "amount": amount}

    try:
        razorpay_order = razorpay_client.order.create(dict(
            amount=order_amount,
            currency=order_currency,
            receipt=order_receipt,
            notes=notes,
            payment_capture="1"
        ))
        return {
            "order_id": razorpay_order["id"],
            "amount": amount,
            "currency": order_currency,
            "razorpay_key_id": settings.RAZORPAY_KEY_ID
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify-payment", response_model=wallet_schema.WalletResponse)
def verify_payment(payload: dict, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    amount = float(payload.get("amount", 0))
    razorpay_payment_id = payload.get("razorpay_payment_id")
    razorpay_order_id = payload.get("razorpay_order_id")
    razorpay_signature = payload.get("razorpay_signature")

    try:
        # Verify Payment Signature
        razorpay_client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Signature verification failed")

    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    # Grant INVENIO tokens equal to the amount purchased
    wallet.balance += amount
    
    # Add transaction to DB
    new_tx = models.Transaction(
        from_wallet=None,  # System emission
        to_wallet=wallet.wallet_id,
        amount=amount,
        tx_hash="pending"
    )
    db.add(new_tx)

    # Add to Custom Blockchain Ledger
    blockchain_tx = Transaction(
        from_wallet="System", 
        to_wallet=str(wallet.wallet_id), 
        amount=amount, 
        tx_type="fiat_purchase",
        metadata={"payment_id": razorpay_payment_id}
    )
    tx_hash = invenio_ledger.add_transaction(blockchain_tx)
    new_tx.tx_hash = tx_hash

    db.commit()
    db.refresh(wallet)
    
    # Mine the block automatically for the demo
    invenio_ledger.mine_pending_transactions()

    return wallet

@router.post("/claim-test-tokens")
def claim_test_tokens(current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Check if Test Mode is ON
    test_mode = db.query(models.SystemSetting).filter(models.SystemSetting.key == "test_mode").first()
    if not test_mode or test_mode.value != "true":
        raise HTTPException(status_code=403, detail="Test Mode is currently OFF.")

    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found.")

    # Rule: Can only claim if balance < 10
    if wallet.balance >= 10:
        raise HTTPException(status_code=400, detail="You already have a sufficient balance. You can claim more when your balance is less than 10 Ʉ.")

    amount_to_add = 100.0
    wallet.balance += amount_to_add

    # Log Transaction
    new_tx = models.Transaction(
        from_wallet=None,
        to_wallet=wallet.wallet_id,
        amount=amount_to_add,
        tx_hash="testing-bypass"
    )
    db.add(new_tx)

    # Blockchain Log
    blockchain_tx = Transaction(
        from_wallet="TestFaucet",
        to_wallet=str(wallet.wallet_id),
        amount=amount_to_add,
        tx_type="test_claim"
    )
    tx_hash = invenio_ledger.add_transaction(blockchain_tx)
    new_tx.tx_hash = tx_hash

    db.commit()
    invenio_ledger.mine_pending_transactions()

    return {"message": f"Successfully claimed {amount_to_add} test tokens!", "new_balance": wallet.balance}

@router.post("/purchase-test-tokens")
def purchase_test_tokens(payload: dict, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    test_mode = db.query(models.SystemSetting).filter(models.SystemSetting.key == "test_mode").first()
    if not test_mode or test_mode.value != "true":
        raise HTTPException(status_code=403, detail="Test Mode is OFF")
    
    amount = float(payload.get("amount", 0))
    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == current_user.id).first()
    wallet.balance += amount
    
    new_tx = models.Transaction(from_wallet=None, to_wallet=wallet.wallet_id, amount=amount, tx_hash="test-bypass")
    db.add(new_tx)
    
    blockchain_tx = Transaction(from_wallet="TestGateway", to_wallet=str(wallet.wallet_id), amount=amount, tx_type="test_purchase")
    tx_hash = invenio_ledger.add_transaction(blockchain_tx)
    new_tx.tx_hash = tx_hash
    
    db.commit()
    invenio_ledger.mine_pending_transactions()
    return {"message": f"Added {amount} tokens", "new_balance": wallet.balance}

@router.get("/test-mode-status")
def get_test_mode_status(db: Session = Depends(get_db)):
    test_mode = db.query(models.SystemSetting).filter(models.SystemSetting.key == "test_mode").first()
    # Default to True for this deployment stage
    if not test_mode:
        return {"test_mode": True}
    return {"test_mode": test_mode.value == "true"}
