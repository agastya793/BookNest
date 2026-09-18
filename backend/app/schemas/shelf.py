from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.book import BookResponse


class ShelfBase(BaseModel):
    """Base schema for shelf properties."""
    name: str = Field(..., min_length=1, max_length=100, description="Shelf name")

    @field_validator("name")
    @classmethod
    def strip_and_validate_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Shelf name cannot be empty or whitespace only")
        return trimmed


class ShelfCreate(ShelfBase):
    """Schema for creating a new shelf."""
    pass


class ShelfUpdate(ShelfBase):
    """Schema for updating/renaming an existing shelf."""
    pass


class AddBookToShelfRequest(BaseModel):
    """Schema for adding a book to a shelf."""
    book_id: UUID


class ShelfBookResponse(BaseModel):
    """Schema representing a book added to a shelf."""
    id: UUID
    shelf_id: UUID
    book_id: UUID
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShelfResponse(BaseModel):
    """Public representation of a shelf."""
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime
    book_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ShelfDetailResponse(ShelfResponse):
    """Detailed shelf representation including member books."""
    books: list[BookResponse] = []
