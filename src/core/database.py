"""
Database connection and session management.

This module provides:
- SQLAlchemy engine configuration with connection pooling
- Session factory for database operations
- Base class for declarative models
- FastAPI dependency for database session management

The connection pool is configured for production use with:
- Connection health checks (pool_pre_ping)
- Reasonable pool size for concurrent requests
- Overflow connections for traffic spikes
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from typing import Generator

from .config import settings


# Create SQLAlchemy engine with connection pooling
# pool_pre_ping: Verifies connections are alive before using them
#                Prevents "connection lost" errors in long-running applications
# pool_size: Number of connections to maintain in the pool (10 = good for moderate load)
# max_overflow: Additional connections allowed beyond pool_size (20 = total of 30 connections max)
# pool_recycle: Recycle connections after 1 hour to prevent stale connections
#               Important for long-running MCP agents that may hold connections
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,      # Verify connections before use
    pool_size=10,            # Base pool size
    max_overflow=20,          # Additional connections allowed
    pool_recycle=3600,       # Recycle connections after 1 hour (prevents stale connections)
    echo=False,              # Set to True for SQL query logging (debug only)
)


# Session factory for creating database sessions
# autocommit=False: Changes require explicit commit() calls
# autoflush=False: Changes are not automatically flushed to DB (better control)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# Base class for all SQLAlchemy declarative models
# All models should inherit from this Base class
Base = declarative_base()


def get_db() -> Generator:
    """
    FastAPI dependency for database session management.
    
    This function provides a database session to route handlers and ensures
    proper cleanup after the request is processed. It follows the dependency
    injection pattern recommended by FastAPI.
    
    Usage:
        ```python
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
        ```
    
    Yields:
        Session: SQLAlchemy database session
    
    Note:
        The session is automatically closed after the request completes,
        even if an exception occurs. This prevents connection leaks.
    
    Example:
        ```python
        # In a route handler
        def create_item(item_data: ItemCreate, db: Session = Depends(get_db)):
            item = Item(**item_data.dict())
            db.add(item)
            db.commit()  # Explicit commit required
            db.refresh(item)
            return item
        ```
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        # Always close the session, even if an exception occurred
        # This ensures connections are returned to the pool
        db.close()
