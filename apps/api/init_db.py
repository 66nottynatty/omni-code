import sys
import os

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database.session import engine
from app.database.models import Base

def init_db():
    print("Initializing database...")
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        print("Vector extension enabled.")
    except Exception as e:
        print(f"Warning: Could not enable vector extension: {e}")
        
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    init_db()
