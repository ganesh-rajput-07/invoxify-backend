from app.database.connection import SessionLocal
from app.database import models

db = SessionLocal()
idea = db.query(models.Idea).first()
if idea:
    print(f"Idea: {idea.idea_id}, Owner: {idea.owner_id}")
    wallet = db.query(models.Wallet).filter(models.Wallet.user_id == idea.owner_id).first()
    print(f"Seller Wallet: {wallet}")
else:
    print("No ideas.")
