from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.shelf import Shelf
from app.models.shelf_book import ShelfBook
from app.schemas.book import BookResponse
from app.schemas.shelf import (
    ShelfCreate,
    ShelfDetailResponse,
    ShelfResponse,
    ShelfUpdate,
    ShelfBookResponse,
)


def create_shelf(db: Session, user_id: UUID, shelf_in: ShelfCreate) -> ShelfResponse:
    """
    Create a new custom shelf for the authenticated user.
    Enforces name uniqueness per user; raises 409 Conflict if a shelf with
    the same name already exists for this user.
    """
    existing = (
        db.query(Shelf)
        .filter(Shelf.user_id == user_id, Shelf.name == shelf_in.name)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Shelf '{shelf_in.name}' already exists",
        )

    shelf = Shelf(user_id=user_id, name=shelf_in.name)
    db.add(shelf)
    try:
        db.commit()
        db.refresh(shelf)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Shelf '{shelf_in.name}' already exists",
        )

    return ShelfResponse(
        id=shelf.id,
        user_id=shelf.user_id,
        name=shelf.name,
        created_at=shelf.created_at,
        book_count=0,
    )


def list_shelves(db: Session, user_id: UUID) -> list[ShelfResponse]:
    """
    List all shelves belonging to the authenticated user along with
    the count of books on each shelf.
    """
    results = (
        db.query(Shelf, func.count(ShelfBook.id).label("book_count"))
        .outerjoin(ShelfBook, ShelfBook.shelf_id == Shelf.id)
        .filter(Shelf.user_id == user_id)
        .group_by(Shelf.id)
        .order_by(Shelf.created_at.asc())
        .all()
    )

    return [
        ShelfResponse(
            id=shelf.id,
            user_id=shelf.user_id,
            name=shelf.name,
            created_at=shelf.created_at,
            book_count=count,
        )
        for shelf, count in results
    ]


def get_shelf_or_404(db: Session, user_id: UUID, shelf_id: UUID) -> Shelf:
    """
    Helper to fetch a shelf verifying user ownership.
    Raises 404 Not Found if shelf does not exist or belongs to another user.
    """
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
    return shelf


def get_shelf(db: Session, user_id: UUID, shelf_id: UUID) -> ShelfResponse:
    """
    Retrieve single shelf metadata and book count.
    """
    shelf = get_shelf_or_404(db, user_id, shelf_id)
    book_count = (
        db.query(func.count(ShelfBook.id))
        .filter(ShelfBook.shelf_id == shelf.id)
        .scalar()
        or 0
    )
    return ShelfResponse(
        id=shelf.id,
        user_id=shelf.user_id,
        name=shelf.name,
        created_at=shelf.created_at,
        book_count=book_count,
    )


def get_shelf_detail(db: Session, user_id: UUID, shelf_id: UUID) -> ShelfDetailResponse:
    """
    Retrieve shelf details along with all books assigned to it.
    """
    shelf = get_shelf_or_404(db, user_id, shelf_id)
    books = (
        db.query(Book)
        .join(ShelfBook, ShelfBook.book_id == Book.id)
        .filter(ShelfBook.shelf_id == shelf_id, Book.user_id == user_id)
        .order_by(ShelfBook.added_at.desc())
        .all()
    )
    book_responses = [BookResponse.model_validate(b) for b in books]
    return ShelfDetailResponse(
        id=shelf.id,
        user_id=shelf.user_id,
        name=shelf.name,
        created_at=shelf.created_at,
        book_count=len(book_responses),
        books=book_responses,
    )


def update_shelf(
    db: Session, user_id: UUID, shelf_id: UUID, shelf_in: ShelfUpdate
) -> ShelfResponse:
    """
    Update/rename a shelf. Enforces name uniqueness among the user's shelves.
    """
    shelf = get_shelf_or_404(db, user_id, shelf_id)

    if shelf.name != shelf_in.name:
        existing = (
            db.query(Shelf)
            .filter(
                Shelf.user_id == user_id,
                Shelf.name == shelf_in.name,
                Shelf.id != shelf_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Shelf '{shelf_in.name}' already exists",
            )
        shelf.name = shelf_in.name
        try:
            db.commit()
            db.refresh(shelf)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Shelf '{shelf_in.name}' already exists",
            )

    book_count = (
        db.query(func.count(ShelfBook.id))
        .filter(ShelfBook.shelf_id == shelf.id)
        .scalar()
        or 0
    )
    return ShelfResponse(
        id=shelf.id,
        user_id=shelf.user_id,
        name=shelf.name,
        created_at=shelf.created_at,
        book_count=book_count,
    )


def delete_shelf(db: Session, user_id: UUID, shelf_id: UUID) -> None:
    """
    Delete a shelf from the user's collection.
    Foreign key CASCADE automatically removes association rows in `shelf_books`,
    while preserving the actual Book entities in the user's library.
    """
    shelf = get_shelf_or_404(db, user_id, shelf_id)
    db.delete(shelf)
    db.commit()


def add_book_to_shelf(
    db: Session, user_id: UUID, shelf_id: UUID, book_id: UUID
) -> ShelfBookResponse:
    """
    Add a book to a custom shelf.
    Validates:
    - Shelf exists and belongs to current user.
    - Book exists and belongs to current user.
    - Book is not already on this shelf (enforces 409 Conflict).
    """
    # Verify shelf ownership
    get_shelf_or_404(db, user_id, shelf_id)

    # Verify book ownership
    book = (
        db.query(Book)
        .filter(Book.id == book_id, Book.user_id == user_id)
        .first()
    )
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found in your library",
        )

    # Check for duplicate association
    existing_assoc = (
        db.query(ShelfBook)
        .filter(ShelfBook.shelf_id == shelf_id, ShelfBook.book_id == book_id)
        .first()
    )
    if existing_assoc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Book is already on this shelf",
        )

    shelf_book = ShelfBook(shelf_id=shelf_id, book_id=book_id)
    db.add(shelf_book)
    try:
        db.commit()
        db.refresh(shelf_book)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Book is already on this shelf",
        )

    return ShelfBookResponse.model_validate(shelf_book)


def remove_book_from_shelf(
    db: Session, user_id: UUID, shelf_id: UUID, book_id: UUID
) -> None:
    """
    Remove a book association from a shelf.
    Validates shelf ownership and existence of association.
    Preserves the book entity in the user's library.
    """
    get_shelf_or_404(db, user_id, shelf_id)

    assoc = (
        db.query(ShelfBook)
        .filter(ShelfBook.shelf_id == shelf_id, ShelfBook.book_id == book_id)
        .first()
    )
    if not assoc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book is not on this shelf",
        )

    db.delete(assoc)
    db.commit()
