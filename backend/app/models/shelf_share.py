import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ShelfShare(Base):
    """Tracks which users have access to a shelf and their role (editor/viewer)."""
    __tablename__ = "shelf_shares"
    __table_args__ = (
        UniqueConstraint("shelf_id", "user_id", name="uq_shelf_share_user"),
        CheckConstraint("role IN ('editor', 'viewer')", name="ck_shelf_share_role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    shelf_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shelves.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    shelf = relationship("Shelf", back_populates="shelf_shares")
    user = relationship("User", back_populates="shelf_shares")

    def __repr__(self):
        return f"<ShelfShare shelf={self.shelf_id} user={self.user_id} role={self.role}>"
