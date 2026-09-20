from datetime import datetime
from typing import Any, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ActivityLogResponse(BaseModel):
    """Single activity log item representation."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    user_name: Optional[str] = None
    action: str
    details: Optional[dict[str, Any]] = None
    shelf_id: Optional[UUID] = None
    shelf_name: Optional[str] = None
    created_at: datetime


class ActivityListResponse(BaseModel):
    """Paginated activity feed response matching server-side pagination standards."""
    items: list[ActivityLogResponse]
    page: int
    page_size: int
    total: int
    total_pages: int
