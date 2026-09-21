from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryResponse
from app.services import dashboard_service

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get aggregated dashboard summary metrics",
)
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns server-side aggregated metrics for the authenticated user's dashboard:
    - Counts by reading status (want_to_read, reading, finished)
    - Books finished this calendar year
    - Average rating of owned books
    - Own shelf with the most books (or null if no qualifying shelf)
    - Books currently lent out (active loans only)
    - Shelves shared with the user (collaborator access)
    """
    return dashboard_service.get_dashboard_summary(db, current_user.id)
