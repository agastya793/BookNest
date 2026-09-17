import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    books = relationship("Book", back_populates="user", cascade="all, delete-orphan")
    shelves = relationship("Shelf", back_populates="user", cascade="all, delete-orphan")
    activity_logs = relationship(
        "ActivityLog", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )
    # Shelf shares where this user is a collaborator
    shelf_shares = relationship(
        "ShelfShare", back_populates="user", cascade="all, delete-orphan"
    )
    # Lendings where this user is the lender
    lendings_as_lender = relationship(
        "Lending",
        back_populates="lender",
        foreign_keys="Lending.lender_id",
        cascade="all, delete-orphan",
    )
    # Lendings where this user is the borrower
    lendings_as_borrower = relationship(
        "Lending",
        back_populates="borrower",
        foreign_keys="Lending.borrower_id",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<User {self.email}>"
