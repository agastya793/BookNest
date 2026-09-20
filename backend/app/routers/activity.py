from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.activity import ActivityListResponse
from app.services import activity_service

router = APIRouter(prefix="/api/activities", tags=["Activities"])


@router.get(
    "",
    response_model=ActivityListResponse,
    status_code=status.HTTP_200_OK,
    summary="List user's activity feed with filtering and server-side pagination",
)
def list_activities(
    page: int = Query(
        1,
        ge=1,
        description="Page number (1-indexed, default 1)",
    ),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Number of activity items per page (default 20, max 100)",
    ),
    action: Optional[str] = Query(
        None,
        description="Optional filter by action (e.g. book_added, status_changed, shelf_shared)",
    ),
    shelf_id: Optional[UUID] = Query(
        None,
        description="Optional filter by specific shelf UUID",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve chronological activity feed items accessible to the authenticated user:
    - Scoped to user's personal activities and currently accessible shared shelves.
    - Full server-side pagination (PostgreSQL COUNT, OFFSET, LIMIT).
    - Optional action and shelf filtering.
    """
    return activity_service.list_activities(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        action_filter=action,
        shelf_id=shelf_id,
    )
