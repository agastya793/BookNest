from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.lending import (
    BorrowedBookResponse,
    LendBookCreate,
    LendingResponse,
)
from app.services import lending_service, realtime_service

router = APIRouter(prefix="/api/lending", tags=["Lending"])


# =============================================================================
# 1. Dedicated & Sub-Collection Routes (Registered FIRST to avoid dynamic match)
# =============================================================================


@router.get(
    "/borrowed",
    response_model=list[BorrowedBookResponse],
    summary="List books currently borrowed by authenticated user",
)
def list_borrowed_books(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve read-only representations of books currently borrowed by current_user.
    - Preserves lender's ownership; borrower gets read-only view.
    - Never duplicates or transfers original Book records.
    """
    return lending_service.list_borrowed_books(db, current_user.id)


@router.get(
    "/borrowed/{book_id}",
    response_model=BorrowedBookResponse,
    summary="Get read-only details of a book borrowed by authenticated user",
)
def get_borrowed_book_detail(
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get read-only view of a specific borrowed book.
    Borrower must be the active borrower of this book; otherwise returns 404.
    """
    return lending_service.get_borrowed_book_detail(db, current_user.id, book_id)


@router.get(
    "/book/{book_id}",
    response_model=list[LendingResponse],
    summary="Get complete lending history for a specific owned book",
)
def get_book_lending_history(
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve complete loan history for a book.
    Only the Book owner may access this endpoint (returns 404 if not owned).
    Registered before /{lending_id} to avoid dynamic UUID route collision.
    """
    return lending_service.get_book_lending_history(db, current_user.id, book_id)


# =============================================================================
# 2. Main Collection Routes
# =============================================================================


@router.post(
    "",
    response_model=LendingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Lend an owned book to another user by email",
)
async def lend_book(
    lend_in: LendBookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Initiate a peer-to-peer book loan:
    - Caller must own the book.
    - Borrower looked up by registered email.
    - Cannot lend to oneself (400).
    - Database-level partial unique index (ix_lending_active_book) enforces single active loan (409 Conflict).
    - Records exactly one ActivityLog entry with action 'book_lent'.
    """
    lending = lending_service.lend_book(db, current_user.id, lend_in)
    lending_dict = lending.model_dump(mode="json")
    await realtime_service.broadcast_lending_event(
        "book_lent",
        lending_dict,
        lending.lender_id,
        lending.borrower_id,
    )
    await realtime_service.broadcast_activity_event(
        {"action": "book_lent", "user_id": str(current_user.id), "book_id": str(lending.book_id)},
        [lending.lender_id, lending.borrower_id],
    )
    return lending


@router.get(
    "",
    response_model=list[LendingResponse],
    summary="List lending records available to authenticated user",
)
def list_lendings(
    role: str = Query(
        "all",
        description="Filter by user role: 'lender', 'borrower', or 'all'",
    ),
    status_filter: str = Query(
        "all",
        alias="status",
        description="Filter by loan status: 'active', 'returned', or 'all'",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List lending records where current user is the lender or borrower.
    Results are ordered by lent_at DESC.
    """
    return lending_service.list_lendings(
        db=db,
        user_id=current_user.id,
        role=role,
        status_filter=status_filter,
    )


# =============================================================================
# 3. Dynamic Parameter Routes (Registered LAST)
# =============================================================================


@router.post(
    "/{lending_id}/return",
    response_model=LendingResponse,
    summary="Mark an active book loan as returned (Book owner only)",
)
async def return_book(
    lending_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mark an active loan as returned:
    - Only the book owner/lender may perform the return action (403 for unauthorized users).
    - Sets is_active = False and returned_at = current UTC time.
    - If already returned, returns 400 Bad Request.
    - Records exactly one ActivityLog entry with action 'book_returned'.
    """
    lending = lending_service.return_book(db, current_user.id, lending_id)
    lending_dict = lending.model_dump(mode="json")
    await realtime_service.broadcast_lending_event(
        "book_returned",
        lending_dict,
        lending.lender_id,
        lending.borrower_id,
    )
    await realtime_service.broadcast_activity_event(
        {"action": "book_returned", "user_id": str(current_user.id), "book_id": str(lending.book_id)},
        [lending.lender_id, lending.borrower_id],
    )
    return lending


@router.get(
    "/{lending_id}",
    response_model=LendingResponse,
    summary="Get details of a specific lending record",
)
def get_lending_detail(
    lending_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve single lending record.
    Allowed only if current user is either the lender or borrower (404 otherwise).
    """
    return lending_service.get_lending_detail(db, current_user.id, lending_id)
