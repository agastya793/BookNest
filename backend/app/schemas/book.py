from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    computed_field,
)
from typing_extensions import Self

BookStatus = Literal["want_to_read", "reading", "finished"]


class BookBase(BaseModel):
    """Base book properties with input validation."""
    title: str = Field(..., min_length=1, max_length=255, description="Book title")
    author: str = Field(..., min_length=1, max_length=255, description="Book author")
    status: BookStatus = Field(default="want_to_read", description="Reading status")
    total_pages: Optional[int] = Field(default=None, ge=1, description="Total pages (must be >= 1 if provided)")
    current_page: int = Field(default=0, ge=0, description="Current page reached (must be >= 0)")
    rating: Optional[int] = Field(default=None, ge=1, le=5, description="Personal rating from 1 to 5 stars")
    notes: Optional[str] = Field(default=None, description="Personal reading notes or thoughts")

    @field_validator("title", "author")
    @classmethod
    def strip_and_validate_non_empty(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Field cannot be empty or whitespace only")
        return trimmed

    @model_validator(mode="after")
    def validate_page_boundaries(self) -> Self:
        if self.total_pages is not None and self.current_page is not None:
            if self.current_page > self.total_pages:
                raise ValueError("current_page cannot exceed total_pages")
        return self


class BookCreate(BookBase):
    """Schema for creating a new book in the personal library."""
    pass


class BookUpdate(BaseModel):
    """Schema for updating an existing book (supports partial updates)."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    author: Optional[str] = Field(default=None, min_length=1, max_length=255)
    status: Optional[BookStatus] = None
    total_pages: Optional[int] = Field(default=None, ge=1)
    current_page: Optional[int] = Field(default=None, ge=0)
    rating: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = None
    finished_date: Optional[datetime] = None

    @field_validator("title", "author")
    @classmethod
    def strip_if_present(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Field cannot be empty or whitespace only")
            return trimmed
        return v

    @model_validator(mode="after")
    def validate_page_boundaries(self) -> Self:
        if self.total_pages is not None and self.current_page is not None:
            if self.current_page > self.total_pages:
                raise ValueError("current_page cannot exceed total_pages")
        return self


class BookResponse(BaseModel):
    """Public representation of a book returned by the API."""
    id: UUID
    user_id: UUID
    title: str
    author: str
    status: str
    total_pages: Optional[int]
    current_page: int
    rating: Optional[int]
    notes: Optional[str]
    finished_date: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # Pydantic v2 ORM mapping from SQLAlchemy Book entity
    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def progress_percentage(self) -> Optional[float]:
        """
        Computed reading progress percentage:
        - round((current_page / total_pages) * 100, 1) when total_pages is present and > 0
        - None when total_pages is null or 0
        """
        if self.total_pages is not None and self.total_pages > 0:
            return round((self.current_page / self.total_pages) * 100, 1)
        return None
