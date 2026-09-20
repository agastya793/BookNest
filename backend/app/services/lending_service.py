from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.activity_log import ActivityLog
from app.models.book import Book
from app.models.lending import Lending
from app.models.user import User
from app.schemas.lending import (
    BorrowedBookResponse,
    LendBookCreate,
    LendingResponse,
)


def lend_book(
    db: Session, lender_id: UUID, lend_in: LendBookCreate
) -> LendingResponse:
    """
    Lend an owned book to another registered BookNest user by email.
    
    Invariants & Security Rules:
    1. Caller must own the book (404 if not found in lender's library).
    2. Borrower must exist in the system (404 if email not found).
    3. Cannot lend to oneself (400 Bad Request).
    4. Defense-in-depth double-lending prevention:
       - Application-level check for existing active loan (409 Conflict).
       - Database-level partial unique index (ix_lending_active_book) catches race conditions (409 Conflict).
    5. Exactly ONE ActivityLog audit entry is recorded (action="book_lent").
    6. Does NOT transfer book ownership or duplicate Book records.
    """
    # 1. Verify Book ownership
    book = (
        db.query(Book)
        .options(selectinload(Book.user))
        .filter(Book.id == lend_in.book_id, Book.user_id == lender_id)
        .first()
    )
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book not found in your library",
        )

    # 2. Look up borrower by case-insensitive email
    borrower = (
        db.query(User)
        .filter(func.lower(User.email) == lend_in.borrower_email.lower())
        .first()
    )
    if not borrower:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{lend_in.borrower_email}' not found",
        )

    # 3. Prevent self-lending
    if borrower.id == lender_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot lend a book to yourself",
        )

    # 4. Application-level check for active loan
    active_loan = (
        db.query(Lending)
        .filter(Lending.book_id == book.id, Lending.is_active == True)
        .first()
    )
    if active_loan:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Book is already actively lent to someone else",
        )

    # 5. Create new active lending
    now = datetime.now(timezone.utc)
    lending = Lending(
        book_id=book.id,
        lender_id=lender_id,
        borrower_id=borrower.id,
        is_active=True,
        lent_at=now,
    )
    db.add(lending)

    # 6. Commit with database-level race protection
    try:
        db.commit()
        db.refresh(lending)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Book is already actively lent to someone else",
        )

    # 7. Record exactly ONE ActivityLog entry
    lender = db.query(User).filter(User.id == lender_id).first()
    activity = ActivityLog(
        user_id=lender_id,
        action="book_lent",
        details={
            "book_id": str(book.id),
            "book_title": book.title,
            "lending_id": str(lending.id),
            "borrower_id": str(borrower.id),
            "borrower_name": borrower.name,
            "borrower_email": borrower.email,
        },
    )
    db.add(activity)
    db.commit()

    return LendingResponse(
        id=lending.id,
        book_id=book.id,
        book_title=book.title,
        book_author=book.author,
        lender_id=lender_id,
        lender_name=lender.name if lender else "Owner",
        lender_email=lender.email if lender else "",
        borrower_id=borrower.id,
        borrower_name=borrower.name,
        borrower_email=borrower.email,
        is_active=lending.is_active,
        lent_at=lending.lent_at,
        returned_at=lending.returned_at,
    )


def return_book(db: Session, user_id: UUID, lending_id: UUID) -> LendingResponse:
    """
    Return an active book loan.
    
    Invariants & Security Rules:
    1. Only the Book owner/lender may return the active loan (403 for unauthorized users).
    2. If loan is already returned -> 400 Bad Request.
    3. Sets is_active = False and returned_at = current UTC time.
    4. Exactly ONE ActivityLog audit entry is recorded (action="book_returned").
    5. Preserves the Book record and owner catalog without deletion or alteration.
    """
    lending = (
        db.query(Lending)
        .options(
            selectinload(Lending.book),
            selectinload(Lending.lender),
            selectinload(Lending.borrower),
        )
        .filter(Lending.id == lending_id)
        .first()
    )
    if not lending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lending record not found",
        )

    # Only the book owner/lender may return the loan per assessment requirements
    if lending.lender_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the book owner can return the active loan",
        )

    # Check if already returned
    if not lending.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book has already been returned",
        )

    now = datetime.now(timezone.utc)
    lending.is_active = False
    lending.returned_at = now

    # Record exactly ONE ActivityLog entry
    activity = ActivityLog(
        user_id=user_id,
        action="book_returned",
        details={
            "book_id": str(lending.book_id),
            "book_title": lending.book.title if lending.book else "",
            "lending_id": str(lending.id),
            "borrower_id": str(lending.borrower_id),
            "borrower_name": lending.borrower.name if lending.borrower else "",
            "returned_by": str(user_id),
        },
    )
    db.add(activity)
    db.commit()
    db.refresh(lending)

    return LendingResponse(
        id=lending.id,
        book_id=lending.book_id,
        book_title=lending.book.title if lending.book else "Unknown Book",
        book_author=lending.book.author if lending.book else "Unknown Author",
        lender_id=lending.lender_id,
        lender_name=lending.lender.name if lending.lender else "Owner",
        lender_email=lending.lender.email if lending.lender else "",
        borrower_id=lending.borrower_id,
        borrower_name=lending.borrower.name if lending.borrower else "Borrower",
        borrower_email=lending.borrower.email if lending.borrower else "",
        is_active=lending.is_active,
        lent_at=lending.lent_at,
        returned_at=lending.returned_at,
    )


def list_lendings(
    db: Session,
    user_id: UUID,
    role: str = "all",
    status_filter: str = "all",
) -> list[LendingResponse]:
    """
    List lending records available to the authenticated user.
    - role='lender': books lent by user
    - role='borrower': books borrowed by user
    - role='all': both
    - status_filter='active', 'returned', 'all'
    Sorted by lent_at DESC.
    """
    query = (
        db.query(Lending)
        .options(
            selectinload(Lending.book),
            selectinload(Lending.lender),
            selectinload(Lending.borrower),
        )
    )

    # Role filter
    if role == "lender":
        query = query.filter(Lending.lender_id == user_id)
    elif role == "borrower":
        query = query.filter(Lending.borrower_id == user_id)
    else:
        query = query.filter(
            or_(Lending.lender_id == user_id, Lending.borrower_id == user_id)
        )

    # Status filter
    if status_filter == "active":
        query = query.filter(Lending.is_active == True)
    elif status_filter == "returned":
        query = query.filter(Lending.is_active == False)

    records = query.order_by(Lending.lent_at.desc()).all()

    return [
        LendingResponse(
            id=l.id,
            book_id=l.book_id,
            book_title=l.book.title if l.book else "Unknown Book",
            book_author=l.book.author if l.book else "Unknown Author",
            lender_id=l.lender_id,
            lender_name=l.lender.name if l.lender else "Owner",
            lender_email=l.lender.email if l.lender else "",
            borrower_id=l.borrower_id,
            borrower_name=l.borrower.name if l.borrower else "Borrower",
            borrower_email=l.borrower.email if l.borrower else "",
            is_active=l.is_active,
            lent_at=l.lent_at,
            returned_at=l.returned_at,
        )
        for l in records
    ]


def get_lending_detail(
    db: Session, user_id: UUID, lending_id: UUID
) -> LendingResponse:
    """
    Retrieve single lending record.
    Accessible ONLY to the lender or borrower (404 to avoid leaking private loans).
    """
    lending = (
        db.query(Lending)
        .options(
            selectinload(Lending.book),
            selectinload(Lending.lender),
            selectinload(Lending.borrower),
        )
        .filter(Lending.id == lending_id)
        .first()
    )
    if not lending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lending record not found",
        )

    if lending.lender_id != user_id and lending.borrower_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lending record not found",
        )

    return LendingResponse(
        id=lending.id,
        book_id=lending.book_id,
        book_title=lending.book.title if lending.book else "Unknown Book",
        book_author=lending.book.author if lending.book else "Unknown Author",
        lender_id=lending.lender_id,
        lender_name=lending.lender.name if lending.lender else "Owner",
        lender_email=lending.lender.email if lending.lender else "",
        borrower_id=lending.borrower_id,
        borrower_name=lending.borrower.name if lending.borrower else "Borrower",
        borrower_email=lending.borrower.email if lending.borrower else "",
        is_active=lending.is_active,
        lent_at=lending.lent_at,
        returned_at=lending.returned_at,
    )


def get_book_lending_history(
    db: Session, user_id: UUID, book_id: UUID
) -> list[LendingResponse]:
    """
    Retrieve complete lending history for a specific book.
    Only the Book owner may access this endpoint (404 if not found in library).
    """
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

    lendings = (
        db.query(Lending)
        .options(
            selectinload(Lending.book),
            selectinload(Lending.lender),
            selectinload(Lending.borrower),
        )
        .filter(Lending.book_id == book_id)
        .order_by(Lending.lent_at.desc())
        .all()
    )

    return [
        LendingResponse(
            id=l.id,
            book_id=l.book_id,
            book_title=l.book.title if l.book else book.title,
            book_author=l.book.author if l.book else book.author,
            lender_id=l.lender_id,
            lender_name=l.lender.name if l.lender else "Owner",
            lender_email=l.lender.email if l.lender else "",
            borrower_id=l.borrower_id,
            borrower_name=l.borrower.name if l.borrower else "Borrower",
            borrower_email=l.borrower.email if l.borrower else "",
            is_active=l.is_active,
            lent_at=l.lent_at,
            returned_at=l.returned_at,
        )
        for l in lendings
    ]


def list_borrowed_books(
    db: Session, user_id: UUID
) -> list[BorrowedBookResponse]:
    """
    Retrieve read-only representations of books currently borrowed by current_user.
    - Only active borrowings (is_active == True).
    - Joins original Book and lender User records.
    - Preserves original ownership (borrower does NOT own or modify the book).
    """
    active_borrowings = (
        db.query(Lending)
        .options(
            selectinload(Lending.book),
            selectinload(Lending.lender),
        )
        .filter(Lending.borrower_id == user_id, Lending.is_active == True)
        .order_by(Lending.lent_at.desc())
        .all()
    )

    return [
        BorrowedBookResponse(
            lending_id=l.id,
            book_id=l.book_id,
            title=l.book.title if l.book else "Unknown Book",
            author=l.book.author if l.book else "Unknown Author",
            total_pages=l.book.total_pages if l.book else None,
            lender_id=l.lender_id,
            lender_name=l.lender.name if l.lender else "Owner",
            lender_email=l.lender.email if l.lender else "",
            lent_at=l.lent_at,
            is_active=l.is_active,
        )
        for l in active_borrowings
        if l.book is not None
    ]


def get_borrowed_book_detail(
    db: Session, user_id: UUID, book_id: UUID
) -> BorrowedBookResponse:
    """
    Retrieve read-only detail of a borrowed book for the active borrower.
    Raises 404 if user is not currently an active borrower of this book.
    """
    lending = (
        db.query(Lending)
        .options(
            selectinload(Lending.book),
            selectinload(Lending.lender),
        )
        .filter(
            Lending.book_id == book_id,
            Lending.borrower_id == user_id,
            Lending.is_active == True,
        )
        .first()
    )
    if not lending or not lending.book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrowed book not found",
        )

    return BorrowedBookResponse(
        lending_id=lending.id,
        book_id=lending.book_id,
        title=lending.book.title,
        author=lending.book.author,
        total_pages=lending.book.total_pages,
        lender_id=lending.lender_id,
        lender_name=lending.lender.name if lending.lender else "Owner",
        lender_email=lending.lender.email if lending.lender else "",
        lent_at=lending.lent_at,
        is_active=lending.is_active,
    )
