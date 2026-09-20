from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class LendBookCreate(BaseModel):
    """Payload to initiate a book loan to another registered user."""
    book_id: UUID = Field(..., description="ID of the book to lend (must belong to lender)")
    borrower_email: str = Field(..., description="Registered email of the borrower")

    @field_validator("borrower_email")
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        trimmed = v.strip().lower()
        if not trimmed or "@" not in trimmed:
            raise ValueError("A valid email address is required")
        return trimmed


class LendingResponse(BaseModel):
    """Full representation of a lending record."""
    id: UUID
    book_id: UUID
    book_title: str
    book_author: str
    lender_id: UUID
    lender_name: str
    lender_email: str
    borrower_id: UUID
    borrower_name: str
    borrower_email: str
    is_active: bool
    lent_at: datetime
    returned_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class BorrowedBookResponse(BaseModel):
    """Read-only representation of a book borrowed by current user."""
    lending_id: UUID
    book_id: UUID
    title: str
    author: str
    total_pages: Optional[int] = None
    lender_id: UUID
    lender_name: str
    lender_email: str
    lent_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class LendingSummary(BaseModel):
    """Compact summary of an active loan for embedding."""
    id: UUID
    borrower_id: UUID
    borrower_name: str
    borrower_email: str
    lent_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
