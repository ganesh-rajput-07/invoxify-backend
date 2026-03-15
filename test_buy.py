from app.database.connection import SessionLocal
from app.database import models

db = SessionLocal()
idea = db.query(models.Idea).first()
if not idea:
    print("No idea")
    exit()

seller = idea.owner_id
# find a buyer that is not the seller
buyer = db.query(models.User).filter(models.User.id != seller).first()
if not buyer:
    print("No second user to buy")
    exit()
print(f"Idea: {idea.idea_id}")
print(f"Seller: {seller}")
print(f"Buyer: {buyer.id}")

buyer_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == buyer.id).first()
seller_wallet = db.query(models.Wallet).filter(models.Wallet.user_id == idea.owner_id).first()

print(f"Buyer Wallet: {buyer_wallet}")
print(f"Seller Wallet: {seller_wallet}")

