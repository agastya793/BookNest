import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class RefreshToken(Base):
    """
    Stores hashed refresh tokens in the database.
    
    Why hashed: If the database is compromised, raw tokens can't be used.
    On refresh, the old token is deleted and a new one is created (rotation).
    On logout, the token is deleted.
    """
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshToken user={self.user_id} expires={self.expires_at}>"
