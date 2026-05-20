import sys
import os

# Add backend dir to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.connection import engine, Base
from app.database import models
from sqlalchemy import text

def reset_database():
    print("🚀 Dropping all tables (Forcing CASCADE)...")
    try:
        with engine.connect() as conn:
            # Drop the entire public schema and recreate it to completely bypass foreign key locks
            conn.execute(text("DROP SCHEMA public CASCADE;"))
            conn.execute(text("CREATE SCHEMA public;"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO postgres;"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
            conn.commit()
        print("✅ Tables completely wiped.")
    except Exception as e:
        print(f"❌ Failed to wipe tables: {e}")
        # Fallback to standard drop
        try:
            Base.metadata.drop_all(bind=engine)
            print("✅ Standard drop succeeded.")
        except Exception as fallback_e:
            pass
        
    print("🚀 Recreating clean tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Clean tables created successfully.")
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")

if __name__ == "__main__":
    reset_database()
