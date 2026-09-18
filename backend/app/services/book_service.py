import math
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.book import Book
from app.models.shelf import Shelf
from app.models.shelf_book import ShelfBook
from app.schemas.book import BookCreate, BookUpdate


def create_book(db: Session, user_id: UUID, book_in: BookCreate) -> Book:
    """
    Create a new book record owned by the authenticated user.
    Enforces status transition rules:
    - Setting status='finished' sets finished_date to current UTC time.
    - If total_pages is present and current_page is 0, auto-completes to total_pages.
    """
    book_data = book_in.model_dump()

    finished_date = None
    if book_data["status"] == "finished":
        finished_date = datetime.now(timezone.utc)
        if book_data.get("total_pages") is not None and book_data.get("current_page", 0) == 0:
            book_data["current_page"] = book_data["total_pages"]
        elif book_data.get("total_pages") is not None and book_data.get("current_page", 0) > 0:
            pass

    book = Book(
        user_id=user_id,
        title=book_data["title"],
        author=book_data["author"],
        status=book_data["status"],
        total_pages=book_data.get("total_pages"),
        current_page=book_data.get("current_page", 0),
        rating=book_data.get("rating"),
        notes=book_data.get("notes"),
        finished_date=finished_date,
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
        .options(selectinload(Book.shelf_books))
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
    query = db.query(Book).filter(Book.user_id == user_id)

    # Optional shelf filter: enforce shelf ownership and association
    if shelf_id:
        shelf = (
            db.query(Shelf)
            .filter(Shelf.id == shelf_id, Shelf.user_id == user_id)
            .first()
        )
        if not shelf:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shelf not found",
            )
        query = query.join(ShelfBook, ShelfBook.book_id == Book.id).filter(
            ShelfBook.shelf_id == shelf_id
        )

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
        query.options(selectinload(Book.shelf_books))
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


def update_book(
    db: Session,
    user_id: UUID,
    book_id: UUID,
    book_in: BookUpdate,
) -> Book:
    """
    Update an existing book with cross-field merge validation and status lifecycle handling.
    Raises 404 if the book does not exist or is not owned by user_id.
    """
    book = get_book(db, user_id, book_id)

    # Cross-field page validation merging payload with existing database state
    effective_current = (
        book_in.current_page if book_in.current_page is not None else book.current_page
    )
    effective_total = (
        book_in.total_pages if book_in.total_pages is not None else book.total_pages
    )

    if effective_total is not None and effective_current > effective_total:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="current_page cannot exceed total_pages",
        )

    update_data = book_in.model_dump(exclude_unset=True)
    new_status = book_in.status if book_in.status is not None else book.status
    old_status = book.status

    # Status Transition Rule: Finished status logic
    if new_status == "finished":
        # Auto-stamp finished_date if transitioning to finished or date unset
        if "finished_date" not in update_data:
            if old_status != "finished" or book.finished_date is None:
                book.finished_date = datetime.now(timezone.utc)

        # Rule 1: If total_pages is known and current_page was not explicitly passed in update, set to total_pages
        if effective_total is not None and "current_page" not in update_data:
            book.current_page = effective_total
    elif old_status == "finished" and new_status != "finished":
        # Transitioning away from finished: clear finished_date unless explicitly provided
        if "finished_date" not in update_data:
            book.finished_date = None

    # Apply provided partial update fields
    for key, value in update_data.items():
        setattr(book, key, value)

    book.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(book)
    return book


def delete_book(db: Session, user_id: UUID, book_id: UUID) -> bool:
    """
    Delete a book owned by the user.
    Raises 404 if the book does not exist or is not owned by user_id.
    """
    book = get_book(db, user_id, book_id)
    db.delete(book)
    db.commit()
    return True
