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
    shelf_ids: list[UUID] = Field(default_factory=list)

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


class PaginatedBooksResponse(BaseModel):
    """Server-side paginated response wrapper for books catalog."""
    items: list[BookResponse] = Field(default_factory=list, description="List of books for current page")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total: int = Field(..., ge=0, description="Total count of books matching the applied filters")
    total_pages: int = Field(..., ge=0, description="Total number of pages")

    model_config = ConfigDict(from_attributes=True)


class BookProgressUpdate(BaseModel):
    """Schema for dedicated reading progress updates."""
    current_page: int = Field(..., ge=0, description="Updated current page number reached")
    notes: Optional[str] = Field(default=None, description="Optional reading notes or reflections")
    rating: Optional[int] = Field(default=None, ge=1, le=5, description="Optional book rating (1-5)")


class ReadingStatsResponse(BaseModel):
    """Aggregated reading statistics for the authenticated user."""
    total_books: int = Field(..., ge=0, description="Total books in personal library")
    books_want_to_read: int = Field(..., ge=0, description="Number of books marked want_to_read")
    books_reading: int = Field(..., ge=0, description="Number of books currently being read")
    books_finished: int = Field(..., ge=0, description="Number of finished books")
    total_pages_read: int = Field(..., ge=0, description="Sum of current pages read across all books")
    completion_rate: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Finished books / total books * 100 (0.0 if total_books == 0)",
    )

    model_config = ConfigDict(from_attributes=True)


class ProgressUpdateResponse(BaseModel):
    """Response returned upon updating reading progress."""
    book: BookResponse
    milestone: Optional[str] = Field(
        default=None,
        description="Milestone reached during this update: 'quarter', 'half', 'three_quarters', 'completed', or None",
    )
    milestone_label: Optional[str] = Field(
        default=None,
        description="Human-readable milestone description",
    )

    model_config = ConfigDict(from_attributes=True)

