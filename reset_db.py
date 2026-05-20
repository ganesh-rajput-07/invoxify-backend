import sys
import os

# Add backend dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import engine, Base
from app.database import models
import sqlalchemy

def reset_database():
    print("🚀 Dropping all tables...")
    try:
        Base.metadata.drop_all(bind=engine)
        print("✅ Tables dropped.")
    except Exception as e:
        print(f"❌ Failed to drop tables: {e}")
        
    print("🚀 Recreating all tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created.")
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")

if __name__ == "__main__":
    reset_database()
