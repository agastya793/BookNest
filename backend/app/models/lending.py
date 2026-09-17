import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Lending(Base):
    """
    Tracks book lending between users.
    
    The partial unique index (ix_lending_active_book) ensures that only ONE 
    active lending can exist per book at the database level. This is the 
    critical constraint that prevents double-lending.
    """
    __tablename__ = "lendings"
    __table_args__ = (
        # CRITICAL: Partial unique index — only one active lending per book
        # This enforces at the DB level that a book can't be lent to two people
        Index(
            "ix_lending_active_book",
            "book_id",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lender_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    borrower_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, index=True
    )
    lent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    returned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    book = relationship("Book", back_populates="lendings")
    lender = relationship(
        "User", back_populates="lendings_as_lender", foreign_keys=[lender_id]
    )
    borrower = relationship(
        "User", back_populates="lendings_as_borrower", foreign_keys=[borrower_id]
    )

    def __repr__(self):
        return f"<Lending book={self.book_id} lender={self.lender_id} borrower={self.borrower_id} active={self.is_active}>"
