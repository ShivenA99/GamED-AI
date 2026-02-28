"""Database session management for FastAPI"""
from sqlalchemy.orm import Session
from fastapi import Depends
from app.db.database import SessionLocal

def get_db_session() -> Session:
    """Dependency injection for database sessions in FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Alias for convenience
get_db = get_db_session


