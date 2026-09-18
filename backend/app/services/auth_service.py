import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID
from fastapi import HTTPException, status
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.models.refresh_token import RefreshToken
from app.models.user import User

# CryptContext configured with bcrypt scheme
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    Enforces the bcrypt 72-byte truncation boundary before hashing.
    """
    byte_len = len(password.encode("utf-8"))
    if byte_len > settings.PASSWORD_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Password must not exceed {settings.PASSWORD_MAX_BYTES} bytes (received {byte_len} bytes)",
        )
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_token(raw_token: str) -> str:
    """
    Produce a deterministic SHA-256 hex digest of a raw token.
    Only this hash is stored in PostgreSQL to protect against database leak theft.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_access_token(user_id: UUID, email: str) -> str:
    """Generate a short-lived signed JWT access token (15 minutes)."""
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(db: Session, user_id: UUID) -> tuple[str, datetime]:
    """
    Generate a long-lived, high-entropy raw refresh token (7 days),
    save only its SHA-256 hash in PostgreSQL, and return (raw_token, expires_at).
    """
    raw_token = secrets.token_urlsafe(64)
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    token_record = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(token_record)
    db.commit()

    return raw_token, expires_at


def rotate_refresh_token(db: Session, raw_token: str) -> tuple[str, str, datetime, User]:
    """
    Transaction-safe refresh token rotation using PostgreSQL row-level locking (SELECT ... FOR UPDATE).
    
    If two concurrent requests attempt to refresh with the same old token simultaneously,
    the row lock serializes them:
    - The first request acquires the lock, deletes the row, and issues a new token pair.
    - The second request unblocks, discovers the row is gone, and receives 401 Unauthorized.
    """
    token_hash = hash_token(raw_token)

    # Pessimistic row-level lock: blocks concurrent transactions targeting the same token
    token_record = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .with_for_update()
        .first()
    )

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Check expiration
    expires_at = token_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        db.delete(token_record)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Find associated user
    user = db.query(User).filter(User.id == token_record.user_id).first()
    if not user:
        db.delete(token_record)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists",
        )

    # Delete the old token (single-use rotation guarantee)
    db.delete(token_record)

    # Generate new refresh token
    new_raw_token = secrets.token_urlsafe(64)
    new_token_hash = hash_token(new_raw_token)
    new_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    new_token_record = RefreshToken(
        user_id=user.id,
        token_hash=new_token_hash,
        expires_at=new_expires_at,
    )
    db.add(new_token_record)
    db.commit()

    # Generate new access token
    new_access_token = create_access_token(user.id, user.email)

    return new_access_token, new_raw_token, new_expires_at, user


def revoke_refresh_token(db: Session, raw_token: str) -> bool:
    """Revoke a refresh token on logout by deleting its SHA-256 hash from PostgreSQL."""
    token_hash = hash_token(raw_token)
    deleted = (
        db.query(RefreshToken)
        .filter(RefreshToken.token_hash == token_hash)
        .delete(synchronize_session=False)
    )
    db.commit()
    return deleted > 0
