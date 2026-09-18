from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.shelf import (
    AddBookToShelfRequest,
    ShelfBookResponse,
    ShelfCreate,
    ShelfDetailResponse,
    ShelfResponse,
    ShelfUpdate,
)
from app.services import shelf_service

router = APIRouter(prefix="/api/shelves", tags=["Shelves"])


@router.post(
    "",
    response_model=ShelfResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new custom shelf",
)
def create_shelf(
    shelf_in: ShelfCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new shelf for the authenticated user.
    Enforces name uniqueness per user; returns 409 Conflict if name already exists.
    """
    return shelf_service.create_shelf(db, current_user.id, shelf_in)


@router.get(
    "",
    response_model=list[ShelfResponse],
    summary="List user's custom shelves",
)
def list_shelves(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all shelves belonging to the authenticated user with book count badges.
    """
    return shelf_service.list_shelves(db, current_user.id)


@router.get(
    "/{shelf_id}",
    response_model=ShelfDetailResponse,
    summary="Get details of a shelf including its books",
)
def get_shelf(
    shelf_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve single shelf metadata and its member books.
    Enforces user ownership: returns 404 if shelf does not exist or belongs to another user.
    """
    return shelf_service.get_shelf_detail(db, current_user.id, shelf_id)


@router.patch(
    "/{shelf_id}",
    response_model=ShelfResponse,
    summary="Rename a custom shelf",
)
def patch_shelf(
    shelf_id: UUID,
    shelf_in: ShelfUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Rename an existing shelf.
    Returns 409 Conflict if the new name collides with another shelf owned by the user.
    """
    return shelf_service.update_shelf(db, current_user.id, shelf_id, shelf_in)


@router.put(
    "/{shelf_id}",
    response_model=ShelfResponse,
    summary="Update a custom shelf",
)
def put_shelf(
    shelf_id: UUID,
    shelf_in: ShelfUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update shelf (PUT semantic compatibility).
    """
    return shelf_service.update_shelf(db, current_user.id, shelf_id, shelf_in)


@router.delete(
    "/{shelf_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a custom shelf",
)
def delete_shelf(
    shelf_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a shelf.
    Association entries in `shelf_books` are cascade deleted, but the actual member books
    remain intact in the user's library.
    """
    shelf_service.delete_shelf(db, current_user.id, shelf_id)
    return None


@router.post(
    "/{shelf_id}/books",
    response_model=ShelfBookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a book to a shelf",
)
def add_book_to_shelf(
    shelf_id: UUID,
    req: AddBookToShelfRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Assign a book to a custom shelf:
    - Verifies shelf ownership (404 if not owned by user).
    - Verifies book ownership (404 if not owned by user).
    - Prevents duplicates (409 Conflict if book is already on shelf).
    """
    return shelf_service.add_book_to_shelf(db, current_user.id, shelf_id, req.book_id)


@router.delete(
    "/{shelf_id}/books/{book_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a book from a shelf",
)
def remove_book_from_shelf(
    shelf_id: UUID,
    book_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a book from a custom shelf.
    The book itself remains in the user's personal library.
    """
    shelf_service.remove_book_from_shelf(db, current_user.id, shelf_id, book_id)
    return None
