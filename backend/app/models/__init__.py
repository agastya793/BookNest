# Import all models so Alembic can detect them for migrations
from app.models.user import User
from app.models.book import Book
from app.models.shelf import Shelf
from app.models.shelf_book import ShelfBook
from app.models.shelf_share import ShelfShare
from app.models.lending import Lending
from app.models.activity_log import ActivityLog
from app.models.refresh_token import RefreshToken

__all__ = [
    "User",
    "Book",
    "Shelf",
    "ShelfBook",
    "ShelfShare",
    "Lending",
    "ActivityLog",
    "RefreshToken",
]
