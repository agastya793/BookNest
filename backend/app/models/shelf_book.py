import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ShelfBook(Base):
    """Join table for the many-to-many relationship between shelves and books."""
    __tablename__ = "shelf_books"
    __table_args__ = (
        UniqueConstraint("shelf_id", "book_id", name="uq_shelf_book"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    shelf_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shelves.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    shelf = relationship("Shelf", back_populates="shelf_books")
    book = relationship("Book", back_populates="shelf_books")

    def __repr__(self):
        return f"<ShelfBook shelf={self.shelf_id} book={self.book_id}>"
