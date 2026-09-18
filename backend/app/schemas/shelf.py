from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
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


class ShelfShareCreate(BaseModel):
    """Schema for inviting a collaborator to a shelf."""
    email: EmailStr
    role: Literal["editor", "viewer"]


class ShelfShareUpdate(BaseModel):
    """Schema for modifying a collaborator's role."""
    role: Literal["editor", "viewer"]


class CollaboratorResponse(BaseModel):
    """Schema representing a collaborator on a shared shelf."""
    id: UUID
    shelf_id: UUID
    user_id: UUID
    user_name: str
    user_email: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ShelfResponse(BaseModel):
    """Public representation of a shelf with role and owner metadata."""
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime
    book_count: int = 0
    role: str = "owner"
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    is_shared: bool = False

    model_config = ConfigDict(from_attributes=True)


class ShelfDetailResponse(ShelfResponse):
    """Detailed shelf representation including member books and collaborators."""
    books: list[BookResponse] = Field(default_factory=list)
    collaborators: list[CollaboratorResponse] = Field(default_factory=list)

