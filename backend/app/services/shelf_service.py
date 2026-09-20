from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.shelf import Shelf
from app.models.shelf_book import ShelfBook
from app.models.shelf_share import ShelfShare
from app.models.user import User
from app.schemas.book import BookResponse
from app.schemas.shelf import (
    CollaboratorResponse,
    ShelfBookResponse,
    ShelfCreate,
    ShelfDetailResponse,
    ShelfResponse,
    ShelfShareCreate,
    ShelfUpdate,
)
from app.services.activity_service import create_activity_log



def get_shelf_with_role(
    db: Session, user_id: UUID, shelf_id: UUID
) -> tuple[Shelf, str]:
    """
    Centralized RBAC permission resolver:
    - If user owns the shelf -> role = "owner"
    - Else if user has an active ShelfShare -> role = "editor" | "viewer"
    - Else -> 404 Not Found (Never leak existence of private shelf to unauthorized users)
    """
    shelf = db.query(Shelf).filter(Shelf.id == shelf_id).first()
    if not shelf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shelf not found",
        )

    if shelf.user_id == user_id:
        return shelf, "owner"

    share = (
        db.query(ShelfShare)
        .filter(ShelfShare.shelf_id == shelf_id, ShelfShare.user_id == user_id)
        .first()
    )
    if share:
        return shelf, share.role

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Shelf not found",
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
        role="owner",
        is_shared=False,
    )


def list_shelves(db: Session, user_id: UUID) -> list[ShelfResponse]:
    """
    List all shelves accessible by the authenticated user:
    1. Shelves owned by the user (role = "owner").
    2. Shelves shared with the user (role = "editor" or "viewer").
    Preserves predictable ordering (owned first, then shared, ordered by created_at).
    """
    # 1. Query owned shelves with book counts
    owned_results = (
        db.query(Shelf, func.count(ShelfBook.id).label("book_count"))
        .outerjoin(ShelfBook, ShelfBook.shelf_id == Shelf.id)
        .filter(Shelf.user_id == user_id)
        .group_by(Shelf.id)
        .order_by(Shelf.created_at.asc())
        .all()
    )

    # Determine which owned shelves currently have collaborators
    shared_owned_shelf_ids = {
        row[0]
        for row in (
            db.query(ShelfShare.shelf_id)
            .join(Shelf, Shelf.id == ShelfShare.shelf_id)
            .filter(Shelf.user_id == user_id)
            .distinct()
            .all()
        )
    }

    owned_shelves = [
        ShelfResponse(
            id=shelf.id,
            user_id=shelf.user_id,
            name=shelf.name,
            created_at=shelf.created_at,
            book_count=count,
            role="owner",
            is_shared=(shelf.id in shared_owned_shelf_ids),
        )
        for shelf, count in owned_results
    ]

    # 2. Query shelves shared with the user
    shared_results = (
        db.query(
            Shelf,
            ShelfShare.role,
            User.name.label("owner_name"),
            User.email.label("owner_email"),
            func.count(ShelfBook.id).label("book_count"),
        )
        .join(ShelfShare, ShelfShare.shelf_id == Shelf.id)
        .join(User, User.id == Shelf.user_id)
        .outerjoin(ShelfBook, ShelfBook.shelf_id == Shelf.id)
        .filter(ShelfShare.user_id == user_id)
        .group_by(Shelf.id, ShelfShare.role, User.name, User.email)
        .order_by(Shelf.created_at.asc())
        .all()
    )

    shared_shelves = [
        ShelfResponse(
            id=shelf.id,
            user_id=shelf.user_id,
            name=shelf.name,
            created_at=shelf.created_at,
            book_count=count,
            role=role,
            owner_name=owner_name,
            owner_email=owner_email,
            is_shared=True,
        )
        for shelf, role, owner_name, owner_email, count in shared_results
    ]

    return owned_shelves + shared_shelves


def get_shelf(db: Session, user_id: UUID, shelf_id: UUID) -> ShelfResponse:
    """
    Retrieve single shelf metadata, active role, and book count.
    """
    shelf, role = get_shelf_with_role(db, user_id, shelf_id)
    book_count = (
        db.query(func.count(ShelfBook.id))
        .filter(ShelfBook.shelf_id == shelf.id)
        .scalar()
        or 0
    )
    owner_user = db.query(User).filter(User.id == shelf.user_id).first()
    share_count = (
        db.query(func.count(ShelfShare.id))
        .filter(ShelfShare.shelf_id == shelf.id)
        .scalar()
        or 0
    )

    return ShelfResponse(
        id=shelf.id,
        user_id=shelf.user_id,
        name=shelf.name,
        created_at=shelf.created_at,
        book_count=book_count,
        role=role,
        owner_name=owner_user.name if owner_user else None,
        owner_email=owner_user.email if owner_user else None,
        is_shared=bool(share_count > 0 or role != "owner"),
    )


def get_shelf_detail(db: Session, user_id: UUID, shelf_id: UUID) -> ShelfDetailResponse:
    """
    Retrieve shelf details along with all assigned books and collaborators.
    Allowed for owner, editor, and viewer.
    """
    shelf, role = get_shelf_with_role(db, user_id, shelf_id)

    books = (
        db.query(Book)
        .join(ShelfBook, ShelfBook.book_id == Book.id)
        .filter(ShelfBook.shelf_id == shelf_id)
        .order_by(ShelfBook.added_at.desc())
        .all()
    )
    book_responses = [BookResponse.model_validate(b) for b in books]

    collaborators_data = (
        db.query(ShelfShare, User.name, User.email)
        .join(User, User.id == ShelfShare.user_id)
        .filter(ShelfShare.shelf_id == shelf_id)
        .order_by(ShelfShare.created_at.asc())
        .all()
    )
    collaborators = [
        CollaboratorResponse(
            id=share.id,
            shelf_id=share.shelf_id,
            user_id=share.user_id,
            user_name=name,
            user_email=email,
            role=share.role,
            created_at=share.created_at,
        )
        for share, name, email in collaborators_data
    ]

    owner_user = db.query(User).filter(User.id == shelf.user_id).first()

    return ShelfDetailResponse(
        id=shelf.id,
        user_id=shelf.user_id,
        name=shelf.name,
        created_at=shelf.created_at,
        book_count=len(book_responses),
        role=role,
        owner_name=owner_user.name if owner_user else None,
        owner_email=owner_user.email if owner_user else None,
        is_shared=bool(len(collaborators) > 0 or role != "owner"),
        books=book_responses,
        collaborators=collaborators,
    )


def update_shelf(
    db: Session, user_id: UUID, shelf_id: UUID, shelf_in: ShelfUpdate
) -> ShelfResponse:
    """
    Update/rename a shelf.
    Only the shelf owner is permitted to rename the shelf (403 for editors/viewers).
    """
    shelf, role = get_shelf_with_role(db, user_id, shelf_id)
    if role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shelf owner can rename shelf",
        )

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
        role="owner",
        is_shared=False,
    )


def delete_shelf(db: Session, user_id: UUID, shelf_id: UUID) -> None:
    """
    Delete a shelf from the user's collection.
    Only the shelf owner is permitted to delete the shelf (403 for editors/viewers).
    CASCADE constraints safely delete join rows in `shelf_books` and `shelf_shares`,
    preserving all member Book records in their owners' libraries.
    """
    shelf, role = get_shelf_with_role(db, user_id, shelf_id)
    if role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shelf owner can delete shelf",
        )

    db.delete(shelf)
    db.commit()


def add_book_to_shelf(
    db: Session, user_id: UUID, shelf_id: UUID, book_id: UUID
) -> ShelfBookResponse:
    """
    Add a book to a shelf:
    - Verifies user has 'owner' or 'editor' access (403 for viewer).
    - Verifies the book belongs to the calling user (cannot add someone else's book).
    - Prevents duplicate book assignment on shelf (409 Conflict).
    """
    shelf, role = get_shelf_with_role(db, user_id, shelf_id)
    if role not in ("owner", "editor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot add books to a shared shelf",
        )

    # Book ownership rule: User may only add their OWN book to the shelf
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
    Remove a book association from a shelf:
    - Verifies user has 'owner' or 'editor' access (403 for viewer).
    - Removes ONLY the shelf association; preserves the Book entity.
    """
    shelf, role = get_shelf_with_role(db, user_id, shelf_id)
    if role not in ("owner", "editor"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Viewers cannot remove books from a shared shelf",
        )

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


# =============================================================================
# Shelf Sharing & Collaborator RBAC Operations
# =============================================================================


def share_shelf(
    db: Session, owner_id: UUID, shelf_id: UUID, share_in: ShelfShareCreate
) -> CollaboratorResponse:
    """
    Invite a collaborator to a custom shelf:
    - Only shelf owner can invite collaborators (403 for others).
    - Invitee looked up by registered email (404 if not found).
    - Cannot invite oneself (400 Bad Request).
    - Cannot duplicate an existing share (409 Conflict).
    - Validates role ('editor' or 'viewer').
    """
    shelf, role = get_shelf_with_role(db, owner_id, shelf_id)
    if role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shelf owner can invite collaborators",
        )

    email_normalized = share_in.email.lower().strip()
    invitee = db.query(User).filter(func.lower(User.email) == email_normalized).first()
    if not invitee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email '{share_in.email}' not found",
        )

    if invitee.id == owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot share shelf with yourself",
        )

    if share_in.role not in ("editor", "viewer"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Collaborator role must be 'editor' or 'viewer'",
        )

    existing_share = (
        db.query(ShelfShare)
        .filter(ShelfShare.shelf_id == shelf_id, ShelfShare.user_id == invitee.id)
        .first()
    )
    if existing_share:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shelf is already shared with this user",
        )

    shelf_share = ShelfShare(
        shelf_id=shelf_id,
        user_id=invitee.id,
        role=share_in.role,
    )
    db.add(shelf_share)

    # Atomically log shelf_shared in the same transaction
    create_activity_log(
        db=db,
        user_id=owner_id,
        action="shelf_shared",
        details={
            "shelf_id": str(shelf.id),
            "shelf_name": shelf.name,
            "collaborator_id": str(invitee.id),
            "collaborator_email": invitee.email,
            "collaborator_name": invitee.name,
            "role": share_in.role,
        },
        shelf_id=shelf.id,
    )

    try:
        db.commit()
        db.refresh(shelf_share)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shelf is already shared with this user",
        )

    return CollaboratorResponse(
        id=shelf_share.id,
        shelf_id=shelf_share.shelf_id,
        user_id=shelf_share.user_id,
        user_name=invitee.name,
        user_email=invitee.email,
        role=shelf_share.role,
        created_at=shelf_share.created_at,
    )


def list_shelf_shares(
    db: Session, user_id: UUID, shelf_id: UUID
) -> list[CollaboratorResponse]:
    """
    List all collaborators on a shelf.
    Allowed for shelf owner, editors, and viewers.
    """
    shelf, role = get_shelf_with_role(db, user_id, shelf_id)
    shares = (
        db.query(ShelfShare, User.name, User.email)
        .join(User, User.id == ShelfShare.user_id)
        .filter(ShelfShare.shelf_id == shelf_id)
        .order_by(ShelfShare.created_at.asc())
        .all()
    )
    return [
        CollaboratorResponse(
            id=share.id,
            shelf_id=share.shelf_id,
            user_id=share.user_id,
            user_name=name,
            user_email=email,
            role=share.role,
            created_at=share.created_at,
        )
        for share, name, email in shares
    ]


def update_shelf_share(
    db: Session, owner_id: UUID, shelf_id: UUID, share_id: UUID, role: str
) -> CollaboratorResponse:
    """
    Change collaborator role (editor <-> viewer):
    - Only shelf owner can update collaborator roles (403 for others).
    - Role must be 'editor' or 'viewer'.
    """
    shelf, current_role = get_shelf_with_role(db, owner_id, shelf_id)
    if current_role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only shelf owner can change collaborator roles",
        )

    if role not in ("editor", "viewer"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Collaborator role must be 'editor' or 'viewer'",
        )

    share = (
        db.query(ShelfShare)
        .filter(ShelfShare.id == share_id, ShelfShare.shelf_id == shelf_id)
        .first()
    )
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collaborator share not found",
        )

    old_role = share.role
    user = db.query(User).filter(User.id == share.user_id).first()

    # Only log and update if role actually changed
    if old_role != role:
        share.role = role
        create_activity_log(
            db=db,
            user_id=owner_id,
            action="shelf_role_changed",
            details={
                "shelf_id": str(shelf.id),
                "shelf_name": shelf.name,
                "collaborator_id": str(share.user_id),
                "collaborator_email": user.email if user else "",
                "collaborator_name": user.name if user else "",
                "old_role": old_role,
                "new_role": role,
            },
            shelf_id=shelf.id,
        )
        db.commit()
        db.refresh(share)

    return CollaboratorResponse(
        id=share.id,
        shelf_id=share.shelf_id,
        user_id=share.user_id,
        user_name=user.name if user else "",
        user_email=user.email if user else "",
        role=share.role,
        created_at=share.created_at,
    )


def delete_shelf_share(
    db: Session, user_id: UUID, shelf_id: UUID, share_id: UUID
) -> None:
    """
    Remove a collaborator from a shelf or leave a shared shelf:
    - Shelf owner can remove any collaborator.
    - Collaborator (editor/viewer) can remove ONLY their own share.
    - Collaborators cannot remove other collaborators (403).
    - Deleting share preserves the shelf and all book records.
    """
    shelf, current_role = get_shelf_with_role(db, user_id, shelf_id)
    share = (
        db.query(ShelfShare)
        .filter(ShelfShare.id == share_id, ShelfShare.shelf_id == shelf_id)
        .first()
    )
    if not share:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collaborator share not found",
        )

    # Permission check: owner can remove any; collaborator can remove only self
    if current_role == "owner":
        pass
    elif share.user_id == user_id:
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Collaborators cannot remove other collaborators",
        )

    target_user = db.query(User).filter(User.id == share.user_id).first()
    create_activity_log(
        db=db,
        user_id=user_id,
        action="shelf_share_removed",
        details={
            "shelf_id": str(shelf.id),
            "shelf_name": shelf.name,
            "collaborator_id": str(share.user_id),
            "collaborator_email": target_user.email if target_user else "",
            "collaborator_name": target_user.name if target_user else "",
            "previous_role": share.role,
            "removed_by": "owner" if current_role == "owner" else "self",
        },
        shelf_id=shelf.id,
    )

    db.delete(share)
    db.commit()

