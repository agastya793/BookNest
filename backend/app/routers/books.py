from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.book import (
    BookCreate,
    BookResponse,
    BookUpdate,
    PaginatedBooksResponse,
    BookProgressUpdate,
    ReadingStatsResponse,
    ProgressUpdateResponse,
)
from app.services import book_service, realtime_service

router = APIRouter(prefix="/api/books", tags=["Books"])


@router.post(
    "",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new book to the personal library",
)
async def create_book(
    book_in: BookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new book in the user's catalog:
    - Input validation ensures current_page <= total_pages.
    - If status is 'finished', automatically populates finished_date and completes current_page if not provided.
    - Ownership is strictly bound to the authenticated user.
    """
    book = book_service.create_book(db, current_user.id, book_in)
    book_dict = BookResponse.model_validate(book).model_dump(mode="json")
    await realtime_service.broadcast_book_event("book_added", book_dict, current_user.id)
    await realtime_service.broadcast_activity_event(
        {"action": "book_added", "user_id": str(current_user.id)},
        [current_user.id],
    )
    return book


@router.get(
    "",
    response_model=PaginatedBooksResponse,
    summary="List user's books with filtering, search, sorting, and pagination",
)
def list_books(
    page: int = Query(
        1,
        ge=1,
        description="Page number (1-indexed, default 1)",
    ),
    page_size: int = Query(
        10,
        ge=1,
        le=100,
        description="Number of books per page (default 10, max 100)",
    ),
    status: Optional[str] = Query(
        None,
        description="Filter by reading status: want_to_read, reading, finished",
    ),
    shelf_id: Optional[UUID] = Query(
        None,
        description="Filter books belonging to a specific custom shelf",
    ),
    search: Optional[str] = Query(
        None,
        description="Case-insensitive keyword search against title or author",
    ),
    sort_by: str = Query(
        "created_at",
        description="Field to sort by: created_at, date_added, updated_at, title, author, rating, current_page",
    ),
    sort_dir: str = Query(
        "desc",
        description="Sort direction: asc or desc",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List books belonging to the authenticated user.
    Supports server-side pagination, status filtering, shelf filtering, search across title/author, and standardized sorting.
    """
    return book_service.list_books(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        status_filter=status,
        shelf_id=shelf_id,
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


@router.get(
    "/stats/summary",
    response_model=ReadingStatsResponse,
    summary="Get aggregated reading statistics for authenticated user",
)
def get_reading_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve reading statistics for the user's catalog:
    - total_books, books_want_to_read, books_reading, books_finished
    - total_pages_read: sum of current pages read across all books
    - completion_rate: finished_books / total_books * 100 (0.0 if empty)
    """
    return book_service.get_reading_stats(db, current_user.id)


@router.post(
    "/{book_id}/progress",
    response_model=ProgressUpdateResponse,
    summary="Update reading progress with milestone tracking and auto-transitions",
)
async def update_book_progress(
    book_id: UUID,
    progress_in: BookProgressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Dedicated endpoint to record reading progress:
    - Automatically advances status:
      * want_to_read -> reading when current_page > 0
      * reading -> finished when current_page reaches total_pages
      * finished -> reading when current_page drops below total_pages
    - Computes milestones reached during the current update (quarter, half, three_quarters, completed)
    - Records audit log in activity_logs (at most one record per update)
    """
    result = book_service.update_book_progress(
        db, current_user.id, book_id, progress_in
    )
    result_dict = ProgressUpdateResponse.model_validate(result).model_dump(mode="json")
    await realtime_service.broadcast_progress_event(result_dict, current_user.id)
    await realtime_service.broadcast_activity_event(
        {"action": "progress_updated", "user_id": str(current_user.id), "book_id": str(book_id)},
        [current_user.id],
    )
    return result


@router.get(
    "/{book_id}",
    response_model=BookResponse,
    summary="Get details of a specific book",
)
def get_book(
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve single book by ID.
    Enforces user ownership: returns 404 if the book does not belong to the user.
    """
    return book_service.get_book(db, current_user.id, book_id)


@router.patch(
    "/{book_id}",
    response_model=BookResponse,
    summary="Partially update an existing book",
)
async def patch_book(
    book_id: UUID,
    book_in: BookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Partially update a book:
    - Merges incoming fields with existing database values for cross-field boundary validation (current_page <= total_pages).
    - Automatically handles status transition side-effects (finished_date setting/clearing).
    """
    book = book_service.update_book(db, current_user.id, book_id, book_in)
    book_dict = BookResponse.model_validate(book).model_dump(mode="json")
    await realtime_service.broadcast_book_event("book_updated", book_dict, current_user.id)
    return book


@router.put(
    "/{book_id}",
    response_model=BookResponse,
    summary="Update an existing book",
)
async def put_book(
    book_id: UUID,
    book_in: BookUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a book (provided for full update and PUT semantic compatibility).
    Routes to the same cross-field validated update handler as PATCH.
    """
    book = book_service.update_book(db, current_user.id, book_id, book_in)
    book_dict = BookResponse.model_validate(book).model_dump(mode="json")
    await realtime_service.broadcast_book_event("book_updated", book_dict, current_user.id)
    return book


@router.delete(
    "/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a book from personal library",
)
async def delete_book(
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a book from the user's library.
    Enforces user ownership: returns 404 if the book does not belong to the user.
    """
    book_service.delete_book(db, current_user.id, book_id)
    await realtime_service.broadcast_book_event("book_deleted", {"id": str(book_id)}, current_user.id)
    return None
