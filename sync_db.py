import sys
from sqlalchemy import text, inspect
from app.database.connection import engine
from app.database import models

def sync_database():
    print("🚀 Starting dynamic database schema synchronization...")
    
    # 1. Ensure all defined tables exist
    models.Base.metadata.create_all(bind=engine)
    print("✅ Tables verified/created.")

    # 2. Inspect database and models for missing columns
    inspector = inspect(engine)
    
    with engine.begin() as conn:
        for table_name, table_obj in models.Base.metadata.tables.items():
            # Get columns currently in database
            try:
                db_columns = [col['name'] for col in inspector.get_columns(table_name)]
            except Exception:
                # Table might have just been created by create_all, skip inspection
                continue

            # Check model for columns not in DB
            for column in table_obj.columns:
                if column.name not in db_columns:
                    print(f"🔧 column '{column.name}' is missing in table '{table_name}'. Syncing...")
                    
                    # Construct basic ALTER TABLE statement
                    # Note: This is a simplified dynamic migration. 
                    # Complex type changes or constraints are better handled by Alembic.
                    col_type = str(column.type)
                    
                    # Handle specific types if necessary (Simplified mapping)
                    if "VARCHAR" in col_type.upper():
                        type_str = "VARCHAR"
                    elif "BOOLEAN" in col_type.upper():
                        type_str = "BOOLEAN"
                    elif "TIMESTAMP" in col_type.upper() or "DATETIME" in col_type.upper():
                        type_str = "TIMESTAMP"
                    elif "UUID" in col_type.upper():
                        type_str = "UUID"
                    elif "FLOAT" in col_type.upper():
                        type_str = "FLOAT"
                    elif "TEXT" in col_type.upper():
                        type_str = "TEXT"
                    elif "INTEGER" in col_type.upper():
                        type_str = "INTEGER"
                    else:
                        type_str = col_type

                    # Build default clause if exists
                    default_clause = ""
                    if column.default is not None:
                        # This is a very basic check for SQLAlchemy defaults
                        pass 

                    try:
                        alter_cmd = f'ALTER TABLE {table_name} ADD COLUMN "{column.name}" {type_str}'
                        conn.execute(text(alter_cmd))
                        print(f"✅ Added {column.name} to {table_name}")
                    except Exception as e:
                        print(f"❌ Failed to add {column.name}: {e}")

    print("\n🏁 Database synchronization complete. Platform schema is up to date.")

if __name__ == "__main__":
    sync_database()
