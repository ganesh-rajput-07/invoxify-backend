import sys
from app.database.connection import SessionLocal
from app.database.models import User

def promote_to_admin(email):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.is_admin = True
        db.commit()
        print(f"User {email} is now an admin.")
    else:
        print(f"User {email} not found.")
    db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python make_admin.py <email>")
    else:
        promote_to_admin(sys.argv[1])
