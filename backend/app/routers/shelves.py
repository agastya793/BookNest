from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.shelf import (
    AddBookToShelfRequest,
    CollaboratorResponse,
    ShelfBookResponse,
    ShelfCreate,
    ShelfDetailResponse,
    ShelfResponse,
    ShelfShareCreate,
    ShelfShareUpdate,
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
    summary="List user's custom and shared shelves",
)
def list_shelves(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all shelves accessible to the authenticated user (owned + shared) with role and book count badges.
    """
    return shelf_service.list_shelves(db, current_user.id)


@router.get(
    "/{shelf_id}",
    response_model=ShelfDetailResponse,
    summary="Get details of a shelf including its books and collaborators",
)
def get_shelf(
    shelf_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve single shelf metadata, assigned books, and collaborators.
    Enforces RBAC: allowed for owner, editor, and viewer. Returns 404 if inaccessible.
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
    Enforces RBAC: only owner can rename shelf (403 for editors/viewers).
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
    Enforces RBAC: only owner can update shelf (403 for editors/viewers).
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
    Enforces RBAC: only owner can delete shelf (403 for editors/viewers).
    CASCADE constraints safely delete join rows while preserving all actual member books.
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
    - Enforces RBAC: allowed for owner and editor (403 for viewer).
    - Enforces book ownership: user can add only their own book (404 if not found).
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
    Remove a book association from a shelf:
    - Enforces RBAC: allowed for owner and editor (403 for viewer).
    - The actual book remains in the user's personal library.
    """
    shelf_service.remove_book_from_shelf(db, current_user.id, shelf_id, book_id)
    return None


# =============================================================================
# Shelf Sharing & Collaborator RBAC Routes
# =============================================================================


@router.post(
    "/{shelf_id}/shares",
    response_model=CollaboratorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite a collaborator to a shelf",
)
def share_shelf(
    shelf_id: UUID,
    share_in: ShelfShareCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Invite a collaborator to a shelf by registered email:
    - Enforces RBAC: only owner can invite collaborators (403 for others).
    - 404 if email is not found in system.
    - 400 if owner tries to share with self.
    - 409 if already shared with this user.
    """
    return shelf_service.share_shelf(db, current_user.id, shelf_id, share_in)


@router.get(
    "/{shelf_id}/shares",
    response_model=list[CollaboratorResponse],
    summary="List collaborators for a shelf",
)
def list_shelf_shares(
    shelf_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all collaborators on a shelf.
    Allowed for owner, editor, and viewer. Returns 404 if user has no access to shelf.
    """
    return shelf_service.list_shelf_shares(db, current_user.id, shelf_id)


@router.patch(
    "/{shelf_id}/shares/{share_id}",
    response_model=CollaboratorResponse,
    summary="Change a collaborator's role",
)
def update_shelf_share(
    shelf_id: UUID,
    share_id: UUID,
    share_in: ShelfShareUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a collaborator's role ('editor' <-> 'viewer').
    Enforces RBAC: only owner can modify roles (403 for others).
    """
    return shelf_service.update_shelf_share(
        db, current_user.id, shelf_id, share_id, share_in.role
    )


@router.delete(
    "/{shelf_id}/shares/{share_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a collaborator or leave a shared shelf",
)
def delete_shelf_share(
    shelf_id: UUID,
    share_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Remove a collaborator from a shelf:
    - Owner can remove any collaborator.
    - Collaborator can remove ONLY their own share (leave shelf).
    - Collaborator cannot remove other collaborators (403).
    """
    shelf_service.delete_shelf_share(db, current_user.id, shelf_id, share_id)
    return None
