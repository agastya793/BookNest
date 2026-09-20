import math
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.activity_log import ActivityLog
from app.models.book import Book
from app.models.lending import Lending
from app.models.shelf import Shelf
from app.models.shelf_book import ShelfBook
from app.schemas.book import BookCreate, BookUpdate, BookProgressUpdate


def create_book(db: Session, user_id: UUID, book_in: BookCreate) -> Book:
    """
    Create a new book record owned by the authenticated user.
    Delegates all validation and status transition lifecycle handling to apply_reading_lifecycle().
    """
    book_data = book_in.model_dump()

    book = Book(
        user_id=user_id,
        title=book_data["title"],
        author=book_data["author"],
        status="want_to_read",
        total_pages=book_data.get("total_pages"),
        current_page=0,
        rating=book_data.get("rating"),
        notes=book_data.get("notes"),
    )

    apply_reading_lifecycle(
        book=book,
        new_current_page=book_data.get("current_page", 0),
        new_total_pages=book_data.get("total_pages"),
        new_status=book_data["status"],
        auto_advance_status=False,
    )

    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def get_book(db: Session, user_id: UUID, book_id: UUID) -> Book:
    """
    Retrieve a book by ID ensuring ownership by user_id.
    Raises 404 Not Found if missing or belonging to another user.
    """
    book = (
        db.query(Book)
        .options(
            selectinload(Book.shelf_books),
            selectinload(Book.lendings).selectinload(Lending.borrower),
        )
        .filter(Book.id == book_id, Book.user_id == user_id)
        .first()
    )
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found",
        )
    return book


def list_books(
    db: Session,
    user_id: UUID,
    page: int = 1,
    page_size: int = 10,
    status_filter: Optional[str] = None,
    shelf_id: Optional[UUID] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
) -> dict:
    """
    List books belonging to the authenticated user with status filtering,
    optional shelf filtering, case-insensitive search against title/author,
    standardized sorting, and server-side pagination executed in PostgreSQL.
    """
    # If shelf_id is specified, verify access via RBAC and filter books on that shelf
    if shelf_id:
        from app.services import shelf_service
        shelf, role = shelf_service.get_shelf_with_role(db, user_id, shelf_id)
        query = (
            db.query(Book)
            .join(ShelfBook, ShelfBook.book_id == Book.id)
            .filter(ShelfBook.shelf_id == shelf_id)
        )
    else:
        query = db.query(Book).filter(Book.user_id == user_id)

    # Optional status filter
    if status_filter:
        query = query.filter(Book.status == status_filter)

    # Optional search filter across title OR author
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter((Book.title.ilike(term)) | (Book.author.ilike(term)))

    # Compute total matching records in database before pagination
    total = query.count()

    # Sort parameter mapping (supporting date_added, rating, title, created_at, etc.)
    sort_column_map = {
        "created_at": Book.created_at,
        "date_added": Book.created_at,
        "updated_at": Book.updated_at,
        "title": Book.title,
        "author": Book.author,
        "rating": Book.rating,
        "current_page": Book.current_page,
    }
    sort_column = sort_column_map.get(sort_by, Book.created_at)

    # Deterministic secondary ordering ensures pagination remains stable across identical sort values
    if sort_dir.lower() == "asc":
        query = query.order_by(sort_column.asc().nulls_last(), Book.id.asc())
    else:
        query = query.order_by(sort_column.desc().nulls_last(), Book.id.asc())

    # Database-level pagination via OFFSET and LIMIT
    offset = (page - 1) * page_size
    items = (
        query.options(
            selectinload(Book.shelf_books),
            selectinload(Book.lendings).selectinload(Lending.borrower),
        )
        .offset(offset)
        .limit(page_size)
        .all()
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }


def calculate_progress_percentage(
    current_page: int, total_pages: Optional[int]
) -> Optional[float]:
    """
    Centralized reading progress percentage calculation.
    Matches BookResponse.progress_percentage:
    round((current_page / total_pages) * 100, 1) when total_pages > 0, else None.
    """
    if total_pages is not None and total_pages > 0:
        return round((current_page / total_pages) * 100, 1)
    return None


def determine_milestone(
    prev_pct: Optional[float], new_pct: Optional[float]
) -> tuple[Optional[str], Optional[str]]:
    """
    Determine if a reading milestone was crossed during the CURRENT update.
    Does NOT repeatedly report milestones if the previous percentage was already at or above threshold.
    - 25%: 'quarter' ("Quarter way through! (25%)")
    - 50%: 'half' ("Halfway mark! (50%)")
    - 75%: 'three_quarters' ("In the final stretch! (75%)")
    - 100%: 'completed' ("Book completed! (100%)")
    """
    if new_pct is None:
        return None, None
    prev = prev_pct if prev_pct is not None else 0.0

    if prev < 100.0 and new_pct >= 100.0:
        return "completed", "Book completed! (100%)"
    if prev < 75.0 and new_pct >= 75.0:
        return "three_quarters", "In the final stretch! (75%)"
    if prev < 50.0 and new_pct >= 50.0:
        return "half", "Halfway mark! (50%)"
    if prev < 25.0 and new_pct >= 25.0:
        return "quarter", "Quarter way through! (25%)"
    return None, None


def apply_reading_lifecycle(
    book: Book,
    new_current_page: Optional[int] = None,
    new_total_pages: Optional[int] = None,
    new_status: Optional[str] = None,
    new_finished_date: Optional[datetime] = None,
    auto_advance_status: bool = False,
) -> dict:
    """
    Single source of truth for:
    1. Validation: current_page non-negative, current_page <= total_pages (raises 422 if violated)
    2. Status resolution:
       - If new_status explicitly provided, it takes precedence.
       - If auto_advance_status=True:
         * current_page > 0 on want_to_read -> auto-advances to 'reading'
         * current_page >= total_pages (with total_pages > 0) -> auto-advances to 'finished'
         * current_page < total_pages on finished book -> auto-reverts to 'reading'
    3. finished_date lifecycle:
       - Sets UTC now on entering finished (if not already set / passed)
       - Clears to None on leaving finished (if not explicitly passed)
    4. Auto-completes current_page = total_pages when entering finished without explicit current_page
    """
    old_page = book.current_page
    old_status = book.status

    effective_current = (
        new_current_page if new_current_page is not None else book.current_page
    )
    effective_total = (
        new_total_pages if new_total_pages is not None else book.total_pages
    )

    # 1. Validation: non-negative and page boundary
    if effective_current < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="current_page cannot be negative",
        )

    if effective_total is not None and effective_current > effective_total:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="current_page cannot exceed total_pages",
        )

    # 2. Status resolution
    resolved_status = old_status
    if new_status is not None:
        resolved_status = new_status
    elif auto_advance_status:
        if (
            effective_total is not None
            and effective_total > 0
            and effective_current >= effective_total
        ):
            resolved_status = "finished"
        elif (
            old_status == "finished"
            and effective_total is not None
            and effective_current < effective_total
        ):
            resolved_status = "reading"
        elif old_status == "want_to_read" and effective_current > 0:
            resolved_status = "reading"

    # 3. Finished date and auto-complete page logic
    if resolved_status == "finished":
        if new_finished_date is not None:
            book.finished_date = new_finished_date
        elif old_status != "finished" or book.finished_date is None:
            book.finished_date = datetime.now(timezone.utc)

        # Rule: If total_pages is known and current_page was not explicitly passed or is 0, complete to total_pages
        if effective_total is not None and (new_current_page is None or effective_current == 0):
            effective_current = effective_total
    elif old_status == "finished" and resolved_status != "finished":
        # Transitioning away from finished: clear finished_date unless explicitly provided
        if new_finished_date is not None:
            book.finished_date = new_finished_date
        else:
            book.finished_date = None

    # Apply resolved values to book
    if new_current_page is not None or (
        resolved_status == "finished"
        and effective_total is not None
    ):
        book.current_page = effective_current

    if new_total_pages is not None:
        book.total_pages = new_total_pages

    book.status = resolved_status

    return {
        "old_page": old_page,
        "new_page": book.current_page,
        "old_status": old_status,
        "new_status": resolved_status,
        "status_changed": old_status != resolved_status,
        "page_changed": old_page != book.current_page,
    }


def update_book(
    db: Session,
    user_id: UUID,
    book_id: UUID,
    book_in: BookUpdate,
) -> Book:
    """
    Update an existing book with cross-field merge validation and status lifecycle handling.
    Raises 404 if the book does not exist or is not owned by user_id.
    Preserves exact Phase 3 PATCH/PUT behavior.
    """
    book = get_book(db, user_id, book_id)
    update_data = book_in.model_dump(exclude_unset=True)

    new_current_page = update_data.get("current_page")
    new_total_pages = update_data.get("total_pages")
    new_status = update_data.get("status")
    new_finished_date = update_data.get("finished_date")

    # Delegate page boundary check and status/finished_date lifecycle to single source of truth
    apply_reading_lifecycle(
        book=book,
        new_current_page=new_current_page,
        new_total_pages=new_total_pages,
        new_status=new_status,
        new_finished_date=new_finished_date,
        auto_advance_status=False,  # Preserves Phase 3 PATCH/PUT behavior
    )

    # Apply remaining provided partial update fields (title, author, rating, notes)
    for key, value in update_data.items():
        if key not in ("current_page", "total_pages", "status", "finished_date"):
            setattr(book, key, value)

    book.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(book)
    return book


def update_book_progress(
    db: Session,
    user_id: UUID,
    book_id: UUID,
    progress_in: BookProgressUpdate,
) -> dict:
    """
    Dedicated reading progress update.
    Reuses get_book() for user ownership and 404 enforcement.
    Reuses apply_reading_lifecycle() for validation and automated status transitions:
    - want_to_read -> reading when current_page > 0
    - reading -> finished when current_page reaches total_pages
    - finished -> reading when current_page drops below total_pages
    Computes single milestone reached during this update.
    Inserts at most ONE ActivityLog record (status_changed if status changed, else progress_updated).
    """
    book = get_book(db, user_id, book_id)

    # Pre-update progress percentage for milestone detection
    prev_pct = calculate_progress_percentage(book.current_page, book.total_pages)

    # Apply lifecycle with auto_advance_status=True
    meta = apply_reading_lifecycle(
        book=book,
        new_current_page=progress_in.current_page,
        auto_advance_status=True,
    )

    # Post-update progress percentage
    new_pct = calculate_progress_percentage(book.current_page, book.total_pages)

    # Milestone reached strictly during THIS update
    milestone, milestone_label = determine_milestone(prev_pct, new_pct)

    # Apply optional reflections / notes / ratings
    if progress_in.notes is not None:
        book.notes = progress_in.notes
    if progress_in.rating is not None:
        book.rating = progress_in.rating

    book.updated_at = datetime.now(timezone.utc)

    # Activity Logging Safeguard: Log at most ONE record, prioritizing status_changed
    if meta["status_changed"]:
        log = ActivityLog(
            user_id=user_id,
            action="status_changed",
            details={
                "book_id": str(book.id),
                "title": book.title,
                "old_status": meta["old_status"],
                "new_status": meta["new_status"],
                "old_page": meta["old_page"],
                "new_page": meta["new_page"],
                "total_pages": book.total_pages,
                "progress_percentage": new_pct,
                "milestone": milestone,
            },
        )
        db.add(log)
    elif meta["page_changed"]:
        log = ActivityLog(
            user_id=user_id,
            action="progress_updated",
            details={
                "book_id": str(book.id),
                "title": book.title,
                "old_page": meta["old_page"],
                "new_page": meta["new_page"],
                "total_pages": book.total_pages,
                "progress_percentage": new_pct,
                "milestone": milestone,
            },
        )
        db.add(log)

    db.commit()
    db.refresh(book)

    return {
        "book": book,
        "milestone": milestone,
        "milestone_label": milestone_label,
    }


def get_reading_stats(db: Session, user_id: UUID) -> dict:
    """
    Aggregates reading statistics for the authenticated user:
    - total_books: total books in personal library
    - books_want_to_read: count with status == 'want_to_read'
    - books_reading: count with status == 'reading'
    - books_finished: count with status == 'finished'
    - total_pages_read: sum of current_page across all user's books
    - completion_rate: (finished_books / total_books) * 100 (0.0 if total_books == 0)
    """
    books = db.query(Book).filter(Book.user_id == user_id).all()
    total_books = len(books)
    books_want_to_read = 0
    books_reading = 0
    books_finished = 0
    total_pages_read = 0

    for b in books:
        if b.status == "want_to_read":
            books_want_to_read += 1
        elif b.status == "reading":
            books_reading += 1
        elif b.status == "finished":
            books_finished += 1
        total_pages_read += b.current_page or 0

    completion_rate = (
        round((books_finished / total_books) * 100, 1) if total_books > 0 else 0.0
    )

    return {
        "total_books": total_books,
        "books_want_to_read": books_want_to_read,
        "books_reading": books_reading,
        "books_finished": books_finished,
        "total_pages_read": total_pages_read,
        "completion_rate": completion_rate,
    }


def delete_book(db: Session, user_id: UUID, book_id: UUID) -> bool:
    """
    Delete a book owned by the user.
    Raises 404 if the book does not exist or is not owned by user_id.
    """
    book = get_book(db, user_id, book_id)
    db.delete(book)
    db.commit()
    return True
