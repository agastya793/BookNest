import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Shelf(Base):
    __tablename__ = "shelves"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_shelf_user_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="shelves")
    shelf_books = relationship(
        "ShelfBook", back_populates="shelf", cascade="all, delete-orphan"
    )
    shelf_shares = relationship(
        "ShelfShare", back_populates="shelf", cascade="all, delete-orphan"
    )
    activity_logs = relationship("ActivityLog", back_populates="shelf")

    def __repr__(self):
        return f"<Shelf {self.name}>"
