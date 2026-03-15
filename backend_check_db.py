from app.database.connection import engine
from sqlalchemy import text
from app.database import models

models.Base.metadata.create_all(bind=engine)
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE users ADD COLUMN is_email_public BOOLEAN DEFAULT false;"))
        conn.commit()
    except Exception as e:
        print("Column might already exist or error:", e)

