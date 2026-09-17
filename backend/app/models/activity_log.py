import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ActivityLog(Base):
    """
    Records key events in the system for the activity feed.
    
    action values:
      - book_added
      - status_changed
      - book_lent
      - book_returned
      - shelf_shared
      - role_changed
      - collaborator_removed
    
    shelf_id is populated when the event relates to a shared shelf,
    used to determine which collaborators should see this event via WebSocket.
    """
    __tablename__ = "activity_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    shelf_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("shelves.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    # Relationships
    user = relationship("User", back_populates="activity_logs")
    shelf = relationship("Shelf", back_populates="activity_logs")

    def __repr__(self):
        return f"<ActivityLog {self.action} by user={self.user_id}>"
