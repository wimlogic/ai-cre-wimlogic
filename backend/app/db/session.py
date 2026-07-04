from typing import Generator
from app.db.database import SessionLocal

def get_db() -> Generator:
    """
    Dependency to get a database session.
    Yields a session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
