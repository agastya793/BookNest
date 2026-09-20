import math
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import Session, joinedload

from app.models.activity_log import ActivityLog
from app.models.shelf import Shelf
from app.models.shelf_share import ShelfShare
from app.schemas.activity import ActivityLogResponse, ActivityListResponse


def create_activity_log(
    db: Session,
    user_id: UUID,
    action: str,
    details: Optional[dict] = None,
    shelf_id: Optional[UUID] = None,
) -> ActivityLog:
    """
    Centralized helper to instantiate and add an ActivityLog record to the active session.
    
    IMPORTANT TRANSACTION INVARIANT:
    - Adds the object to the current SQLAlchemy session.
    - Does NOT call db.commit().
    - The business operation and this audit log record are finalized in a SINGLE commit,
      guaranteeing that audit logs never survive failed business operations.
    """
    log = ActivityLog(
        user_id=user_id,
        action=action,
        details=details or {},
        shelf_id=shelf_id,
    )
    db.add(log)
    return log


def to_activity_response(log: ActivityLog) -> ActivityLogResponse:
    """Map SQLAlchemy ActivityLog entity to Pydantic ActivityLogResponse schema."""
    user_name = log.user.name if log.user else (log.details.get("user_name") if log.details else None)
    shelf_name = log.shelf.name if log.shelf else (log.details.get("shelf_name") if log.details else None)
    return ActivityLogResponse(
        id=log.id,
        user_id=log.user_id,
        user_name=user_name,
        action=log.action,
        details=log.details,
        shelf_id=log.shelf_id,
        shelf_name=shelf_name,
        created_at=log.created_at,
    )


def list_activities(
    db: Session,
    user_id: UUID,
    page: int = 1,
    page_size: int = 20,
    action_filter: Optional[str] = None,
    shelf_id: Optional[UUID] = None,
) -> dict:
    """
    List activities accessible to the user with server-side pagination, ordering, and filtering.
    
    Visibility & Security Rules:
    1. Personal activities (shelf_id is NULL):
       - Visible only to the user whose personal library activity generated them.
    2. Shared shelf activities (shelf_id is NOT NULL):
       - Visible to users who CURRENTLY have access to that shelf (as owner or active collaborator).
       - If a collaborator's access was removed, they cannot retrieve activities for that shelf.
       - Unrelated users cannot see those activities.
    3. Lending activities:
       - Visible to participants: lender (user_id) or borrower (details ->> 'borrower_id').
       - Unrelated users cannot see them.
    4. Database-level pagination:
       - COUNT executed before LIMIT/OFFSET.
       - Primary ordering: created_at DESC, secondary ordering: id DESC.
    """
    # 1. Parameter normalization and validation
    page = max(1, page)
    page_size = max(1, min(100, page_size))

    # 2. Specific shelf filter requested
    if shelf_id is not None:
        from app.services import shelf_service
        # Verify caller currently has access to this shelf (raises 404 if inaccessible or nonexistent)
        shelf_service.get_shelf_with_role(db, user_id, shelf_id)
        query = db.query(ActivityLog).filter(ActivityLog.shelf_id == shelf_id)
    else:
        # 3. General activity feed visibility scoping:
        owned_query = db.query(Shelf.id).filter(Shelf.user_id == user_id)
        shared_query = db.query(ShelfShare.shelf_id).filter(ShelfShare.user_id == user_id)
        accessible_shelves_query = owned_query.union(shared_query)

        # Scoped visibility conditions:
        # A. Shared shelf activities where user currently has access to the shelf
        cond_shared_shelf = and_(
            ActivityLog.shelf_id.isnot(None),
            ActivityLog.shelf_id.in_(accessible_shelves_query),
        )

        # B. Personal activities (shelf_id is None) owned by the current user
        cond_personal = and_(
            ActivityLog.shelf_id.is_(None),
            ActivityLog.user_id == user_id,
        )

        # C. Lending activities where user is the borrower (recorded in JSON details)
        cond_borrower_lending = and_(
            ActivityLog.action.in_(["book_lent", "book_returned"]),
            func.json_extract_path_text(ActivityLog.details, "borrower_id") == str(user_id),
        )

        query = db.query(ActivityLog).filter(
            or_(cond_shared_shelf, cond_personal, cond_borrower_lending)
        )

    # 4. Action filtering if provided (supports single action or comma-separated list)
    if action_filter and action_filter.strip():
        actions = [a.strip() for a in action_filter.strip().split(",") if a.strip()]
        if len(actions) == 1:
            query = query.filter(ActivityLog.action == actions[0])
        elif len(actions) > 1:
            query = query.filter(ActivityLog.action.in_(actions))

    # 5. Calculate total matching records in database before pagination
    total = query.count()

    # 6. Primary ordering: created_at DESC; secondary deterministic ordering: id DESC
    query = query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())

    # 7. Database-level pagination via OFFSET and LIMIT
    offset = (page - 1) * page_size
    items = (
        query.options(
            joinedload(ActivityLog.user),
            joinedload(ActivityLog.shelf),
        )
        .offset(offset)
        .limit(page_size)
        .all()
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    response_items = [to_activity_response(log) for log in items]

    return {
        "items": response_items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }
