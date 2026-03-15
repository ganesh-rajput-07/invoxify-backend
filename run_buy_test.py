from app.database.connection import SessionLocal
from app.database import models
from app.routes.marketplace_routes import buy_idea

db = SessionLocal()
# Grab an idea
idea = db.query(models.Idea).first()
if not idea:
    print("NO IDEA FOUND")
    exit()

# Grab a buyer
buyer = db.query(models.User).filter(models.User.id != idea.owner_id).first()
if not buyer:
    print("NO BUYER FOUND")
    exit()

# Add lots of money to buyer to avoid 400
wallet = db.query(models.Wallet).filter(models.Wallet.user_id == buyer.id).first()
wallet.balance = 1000000.0
db.commit()

# Call method
try:
    res = buy_idea(str(idea.idea_id), buyer, db)
    print("SUCCESS", res)
except Exception as e:
    import traceback
    traceback.print_exc()

