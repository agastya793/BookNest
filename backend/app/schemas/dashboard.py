from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class StatusCounts(BaseModel):
    """Reading status distribution counts."""
    want_to_read: int = Field(default=0, description="Count of books with status want_to_read")
    reading: int = Field(default=0, description="Count of books with status reading")
    finished: int = Field(default=0, description="Count of books with status finished")


class TopShelfSummary(BaseModel):
    """Details of the owned shelf with the most books assigned."""
    id: UUID = Field(..., description="Shelf UUID")
    name: str = Field(..., description="Shelf name")
    book_count: int = Field(..., ge=1, description="Number of books on this shelf")


class DashboardSummaryResponse(BaseModel):
    """
    Dedicated dashboard summary aggregating key personal library metrics:
    1. Status counts (want_to_read, reading, finished)
    2. Books finished this calendar year
    3. Average rating of owned books
    4. Top shelf by book count (or null if no qualifying shelf)
    5. Books currently lent out (active peer loans)
    6. Shelves shared with the user (collaborator access)
    """
    status_counts: StatusCounts
    books_finished_this_year: int = Field(default=0, ge=0)
    average_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    shelf_with_most_books: Optional[TopShelfSummary] = None
    books_currently_lent_out: int = Field(default=0, ge=0)
    shelves_shared_with_me: int = Field(default=0, ge=0)
