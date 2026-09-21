from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.book import Book
from app.models.lending import Lending
from app.models.shelf import Shelf
from app.models.shelf_book import ShelfBook
from app.models.shelf_share import ShelfShare
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    StatusCounts,
    TopShelfSummary,
)


def get_dashboard_summary(db: Session, user_id: UUID) -> DashboardSummaryResponse:
    """
    Calculate the dashboard summary for the authenticated user using
    server-side SQL / database aggregation in PostgreSQL.

    Metrics aggregated:
    1. status_counts: Counts of user's books grouped by status (want_to_read, reading, finished)
    2. books_finished_this_year: Count of finished books where finished_date falls in the current calendar year
    3. average_rating: Average rating of user's rated books (0.0 if no ratings)
    4. shelf_with_most_books: Owned shelf with the highest book count (or None if no books in shelves),
       with deterministic tie-breaking (order by book_count DESC, shelf name ASC, shelf ID ASC)
    5. books_currently_lent_out: Count of distinct books owned by user with an active lending record
    6. shelves_shared_with_me: Count of shelves where user is a collaborator (excluding own shelves)
    """
    # 1. Status Counts (SQL GROUP BY aggregation)
    status_counts_dict = {
        "want_to_read": 0,
        "reading": 0,
        "finished": 0,
    }
    status_rows = (
        db.query(Book.status, func.count(Book.id))
        .filter(Book.user_id == user_id)
        .group_by(Book.status)
        .all()
    )
    for st, count in status_rows:
        if st in status_counts_dict:
            status_counts_dict[st] = count

    # 2. Books Finished This Year (Current calendar year, sargable UTC bounds)
    now = datetime.now(timezone.utc)
    current_year = now.year
    start_of_year = datetime(current_year, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    start_of_next_year = datetime(current_year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    books_finished_this_year = (
        db.query(func.count(Book.id))
        .filter(
            Book.user_id == user_id,
            Book.status == "finished",
            Book.finished_date.isnot(None),
            Book.finished_date >= start_of_year,
            Book.finished_date < start_of_next_year,
        )
        .scalar()
    ) or 0

    # 3. Average Rating (SQL AVG over rated books owned by user)
    avg_rating_val = (
        db.query(func.avg(Book.rating))
        .filter(
            Book.user_id == user_id,
            Book.rating.isnot(None),
        )
        .scalar()
    )
    average_rating = (
        round(float(avg_rating_val), 1) if avg_rating_val is not None else 0.0
    )

    # 4. Shelf With Most Books (SQL GROUP BY & COUNT on ShelfBook, deterministic tie-breaking)
    # Primary library shelves owned by authenticated user; returns None if no qualifying shelf
    top_shelf_row = (
        db.query(
            Shelf.id,
            Shelf.name,
            func.count(ShelfBook.id).label("book_count"),
        )
        .join(ShelfBook, ShelfBook.shelf_id == Shelf.id)
        .filter(Shelf.user_id == user_id)
        .group_by(Shelf.id, Shelf.name)
        .having(func.count(ShelfBook.id) > 0)
        .order_by(
            func.count(ShelfBook.id).desc(),
            Shelf.name.asc(),
            Shelf.id.asc(),
        )
        .first()
    )
    shelf_with_most_books = None
    if top_shelf_row:
        shelf_with_most_books = TopShelfSummary(
            id=top_shelf_row[0],
            name=top_shelf_row[1],
            book_count=top_shelf_row[2],
        )

    # 5. Books Currently Lent Out (Count DISTINCT Book.id with active loan)
    books_currently_lent_out = (
        db.query(func.count(func.distinct(Book.id)))
        .join(Lending, Lending.book_id == Book.id)
        .filter(
            Book.user_id == user_id,
            Lending.is_active == True,
        )
        .scalar()
    ) or 0

    # 6. Shelves Shared With Me (Collaborator access on shelves owned by others)
    shelves_shared_with_me = (
        db.query(func.count(ShelfShare.id))
        .join(Shelf, Shelf.id == ShelfShare.shelf_id)
        .filter(
            ShelfShare.user_id == user_id,
            Shelf.user_id != user_id,
        )
        .scalar()
    ) or 0

    return DashboardSummaryResponse(
        status_counts=StatusCounts(**status_counts_dict),
        books_finished_this_year=books_finished_this_year,
        average_rating=average_rating,
        shelf_with_most_books=shelf_with_most_books,
        books_currently_lent_out=books_currently_lent_out,
        shelves_shared_with_me=shelves_shared_with_me,
    )
