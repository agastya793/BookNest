from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings


# Synchronous engine — kept simple intentionally (no async complexity)
# Using psycopg v3 driver (postgresql+psycopg)
db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
engine = create_engine(db_url, echo=False)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def get_db():
    """FastAPI dependency that provides a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
