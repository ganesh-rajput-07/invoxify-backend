from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import models
from app.database.connection import engine
from app.routes import auth_routes, wallet_routes, idea_routes, marketplace_routes, user_routes, problem_routes, admin_routes
from app.config.settings import settings

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Auto-migrate missing columns for prototype
from sqlalchemy import text
try:
    with engine.begin() as conn:
        try: conn.execute(text("ALTER TABLE ideas ADD COLUMN plan_1m_price FLOAT"))
        except: pass
        try: conn.execute(text("ALTER TABLE ideas ADD COLUMN plan_3m_price FLOAT"))
        except: pass
        try: conn.execute(text("ALTER TABLE ideas ADD COLUMN plan_6m_price FLOAT"))
        except: pass
        try: conn.execute(text("ALTER TABLE idea_purchases ADD COLUMN plan_duration_months INTEGER"))
        except: pass
        try: conn.execute(text("ALTER TABLE idea_purchases ADD COLUMN expiry_date TIMESTAMP"))
        except: pass
except Exception as e:
    print("Auto-migration skipped:", e)


app = FastAPI(title=settings.PROJECT_NAME)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_routes.router)
app.include_router(wallet_routes.router)
app.include_router(idea_routes.router)
app.include_router(marketplace_routes.router)
app.include_router(user_routes.router)
app.include_router(problem_routes.router)
app.include_router(admin_routes.router)

from sqlalchemy import text
from app.database.connection import SessionLocal

@app.get("/debug/sync-db")
def sync_db_schema():
    """Manually add missing bargaining columns to the DB if they don't exist"""
    db = SessionLocal()
    results = []
    try:
        # Add counter_price if missing
        try:
            db.execute(text("ALTER TABLE ownership_bids ADD COLUMN counter_price FLOAT"))
            db.commit()
            results.append("Added counter_price")
        except Exception as e:
            db.rollback()
            results.append(f"counter_price already exists or error: {str(e)}")

        # Add last_action_by if missing
        try:
            db.execute(text("ALTER TABLE ownership_bids ADD COLUMN last_action_by VARCHAR DEFAULT 'buyer'"))
            db.commit()
            results.append("Added last_action_by")
        except Exception as e:
            db.rollback()
            results.append(f"last_action_by column exists")

        # Data patch: Fill NULL last_action_by which might have was added but not filled
        try:
            db.execute(text("UPDATE ownership_bids SET last_action_by = 'buyer' WHERE last_action_by IS NULL"))
            db.commit()
            results.append("Patched legacy null records for last_action_by")
        except Exception as e:
            db.rollback()
            results.append(f"Data patch skipped or error: {str(e)}")
            
        # Add is_public to ideas if missing
        try:
            db.execute(text("ALTER TABLE ideas ADD COLUMN is_public BOOLEAN DEFAULT TRUE"))
            db.commit()
            results.append("Added is_public to ideas")
        except Exception as e:
            db.rollback()
            results.append(f"is_public already exists on ideas")

        # Set default for existing records
        try:
            db.execute(text("UPDATE ideas SET is_public = TRUE WHERE is_public IS NULL"))
            db.commit()
            results.append("Patched legacy null records for is_public")
        except:
             db.rollback()

        # Add licensing columns to ideas
        try:
            db.execute(text("ALTER TABLE ideas ADD COLUMN plan_1m_price FLOAT"))
            db.execute(text("ALTER TABLE ideas ADD COLUMN plan_3m_price FLOAT"))
            db.execute(text("ALTER TABLE ideas ADD COLUMN plan_6m_price FLOAT"))
            db.commit()
            results.append("Added plan pricing to ideas")
        except Exception as e:
            db.rollback()
            results.append(f"plan pricing already exists on ideas or error: {str(e)}")

        # Add license expiry columns to idea_purchases
        try:
            db.execute(text("ALTER TABLE idea_purchases ADD COLUMN plan_duration_months INTEGER"))
            db.execute(text("ALTER TABLE idea_purchases ADD COLUMN expiry_date TIMESTAMP"))
            db.commit()
            results.append("Added expiry logic to idea_purchases")
        except Exception as e:
            db.rollback()
            results.append(f"expiry_date already exists on idea_purchases or error: {str(e)}")
            
        return {"status": "Migration complete", "details": results}
    finally:
        db.close()

@app.get("/")
def read_root():
    return {
        "platform": settings.PROJECT_NAME,
        "status": "Online",
        "currency": "InvenIO (Ʉ)"
    }

@app.get("/kaithheathcheck")
def health():
    return {"status": "ok"}