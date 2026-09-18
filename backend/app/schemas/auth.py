import re
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from app.config import settings

# Documented special characters allowed in passwords
SPECIAL_CHARACTERS = r"!@#$%^&*()_+\-=\[\]{}|;:,.<>?"
SPECIAL_CHAR_REGEX = re.compile(f"[{re.escape('!@#$%^&*()_+-=[]{}|;:,.<>?')}]")


class UserCreate(BaseModel):
    """Schema for user registration."""
    name: str = Field(..., min_length=1, max_length=100, description="User's full name")
    email: EmailStr = Field(..., description="Valid email address")
    password: str = Field(..., description="User's password meeting complexity rules")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Name cannot be empty or whitespace only")
        return trimmed

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        # Minimum character length
        if len(v) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long")
        
        # Bcrypt maximum 72-byte limit validation
        byte_length = len(v.encode("utf-8"))
        if byte_length > settings.PASSWORD_MAX_BYTES:
            raise ValueError(
                f"Password must not exceed {settings.PASSWORD_MAX_BYTES} bytes (bcrypt limitation; currently {byte_length} bytes)"
            )

        # Character complexity enforcement
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter (A-Z)")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter (a-z)")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one numeric digit (0-9)")
        if not SPECIAL_CHAR_REGEX.search(v):
            raise ValueError("Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)")

        return v


class UserLogin(BaseModel):
    """Schema for user login credentials."""
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Plaintext password")


class UserResponse(BaseModel):
    """Public user profile (never exposes password hash or sensitive internals)."""
    id: UUID
    name: str
    email: str
    created_at: datetime

    # Pydantic v2 ORM serialization from SQLAlchemy User model
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Response returned upon successful authentication or token refresh."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    """Standard generic message response."""
    message: str
