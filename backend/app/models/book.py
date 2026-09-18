import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("status IN ('want_to_read', 'reading', 'finished')", name="ck_book_status"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_book_rating"),
        CheckConstraint("current_page >= 0", name="ck_book_current_page"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="want_to_read", index=True
    )
    total_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_page: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    finished_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="books")
    shelf_books = relationship(
        "ShelfBook", back_populates="book", cascade="all, delete-orphan"
    )
    lendings = relationship(
        "Lending", back_populates="book", cascade="all, delete-orphan"
    )

    @property
    def shelf_ids(self) -> list[uuid.UUID]:
        return [sb.shelf_id for sb in self.shelf_books]

    def __repr__(self):
        return f"<Book {self.title} by {self.author}>"
