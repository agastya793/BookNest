"""
BookNest Seed Script
Creates deterministic, idempotent sample data for demonstration and assessment:
- 2 demo users (Demo Owner, Demo Collaborator) with bcrypt-hashed passwords
- 7 sample books covering want_to_read, reading, and finished with realistic pages & ratings
- 4 sample shelves with varied book counts
- 2 shelf shares: "Favorites" (editor) and "Backend & Tech" (viewer)
- 1 active peer loan (Domain-Driven Design lent from Owner to Collaborator)
- Idempotent activity log entries matching the seeded events

Usage:
  cd backend
  .\\venv\\Scripts\\python seed.py
"""
import sys
from datetime import datetime, timezone, timedelta
from app.database import SessionLocal
from app.models.activity_log import ActivityLog
from app.models.book import Book
from app.models.lending import Lending
from app.models.shelf import Shelf
from app.models.shelf_book import ShelfBook
from app.models.shelf_share import ShelfShare
from app.models.user import User
from app.services.auth_service import hash_password

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEMO_PASSWORD = "DemoPassword123!"


def seed_database():
    print("Seeding BookNest database with sample demonstration data...\n")
    now = datetime.now(timezone.utc)

    stats = {
        "users_created": 0,
        "users_reused": 0,
        "books_created": 0,
        "books_reused": 0,
        "shelves_created": 0,
        "shelves_reused": 0,
        "shelf_links_created": 0,
        "shelf_links_reused": 0,
        "shelf_shares_created": 0,
        "shelf_shares_reused": 0,
        "lendings_created": 0,
        "lendings_reused": 0,
        "activities_created": 0,
        "activities_reused": 0,
    }

    with SessionLocal() as db:
        # -------------------------------------------------------------------------
        # 1. Demo Users
        # -------------------------------------------------------------------------
        users_def = [
            {"email": "owner@booknest.demo", "name": "Demo Owner"},
            {"email": "collaborator@booknest.demo", "name": "Demo Collaborator"},
        ]
        users = {}
        for u in users_def:
            user = db.query(User).filter(User.email == u["email"]).first()
            if not user:
                user = User(
                    name=u["name"],
                    email=u["email"],
                    password_hash=hash_password(DEMO_PASSWORD),
                )
                db.add(user)
                db.flush()
                stats["users_created"] += 1
            else:
                stats["users_reused"] += 1
            users[u["email"]] = user

        owner = users["owner@booknest.demo"]
        collaborator = users["collaborator@booknest.demo"]

        # -------------------------------------------------------------------------
        # 2. Sample Books
        # -------------------------------------------------------------------------
        books_def = [
            # Owner's Books
            {
                "user": owner,
                "title": "Clean Architecture",
                "author": "Robert C. Martin",
                "status": "finished",
                "total_pages": 352,
                "current_page": 352,
                "rating": 5,
                "notes": "Essential principles of software architecture and craftsmanship.",
                "finished_date": now - timedelta(days=25),
            },
            {
                "user": owner,
                "title": "Designing Data-Intensive Applications",
                "author": "Martin Kleppmann",
                "status": "reading",
                "total_pages": 616,
                "current_page": 280,
                "rating": 5,
                "notes": "In-depth guide to reliability, scalability, and distributed data systems.",
                "finished_date": None,
            },
            {
                "user": owner,
                "title": "The Pragmatic Programmer",
                "author": "David Thomas, Andrew Hunt",
                "status": "want_to_read",
                "total_pages": 352,
                "current_page": 0,
                "rating": None,
                "notes": "Foundational tips from journey to mastery in software development.",
                "finished_date": None,
            },
            {
                "user": owner,
                "title": "Domain-Driven Design",
                "author": "Eric Evans",
                "status": "reading",
                "total_pages": 560,
                "current_page": 150,
                "rating": 4,
                "notes": "Tackling software complexity through ubiquitous language and bounded contexts.",
                "finished_date": None,
            },
            {
                "user": owner,
                "title": "Site Reliability Engineering",
                "author": "Betsy Beyer, Chris Jones, Niall Murphy",
                "status": "finished",
                "total_pages": 550,
                "current_page": 550,
                "rating": 4,
                "notes": "How Google operates production scale infrastructure with SLA/SLO rigor.",
                "finished_date": now - timedelta(days=8),
            },
            # Collaborator's Books
            {
                "user": collaborator,
                "title": "Refactoring",
                "author": "Martin Fowler",
                "status": "reading",
                "total_pages": 448,
                "current_page": 120,
                "rating": 5,
                "notes": "Improving design of existing code through proven transformations.",
                "finished_date": None,
            },
            {
                "user": collaborator,
                "title": "Patterns of Enterprise Application Architecture",
                "author": "Martin Fowler",
                "status": "want_to_read",
                "total_pages": 560,
                "current_page": 0,
                "rating": None,
                "notes": "Classic patterns for enterprise systems and relational mapping.",
                "finished_date": None,
            },
        ]

        books = {}
        for b_spec in books_def:
            key = (b_spec["user"].id, b_spec["title"])
            book = (
                db.query(Book)
                .filter(Book.user_id == b_spec["user"].id, Book.title == b_spec["title"])
                .first()
            )
            if not book:
                book = Book(
                    user_id=b_spec["user"].id,
                    title=b_spec["title"],
                    author=b_spec["author"],
                    status=b_spec["status"],
                    total_pages=b_spec["total_pages"],
                    current_page=b_spec["current_page"],
                    rating=b_spec["rating"],
                    notes=b_spec["notes"],
                    finished_date=b_spec["finished_date"],
                )
                db.add(book)
                db.flush()
                stats["books_created"] += 1
            else:
                stats["books_reused"] += 1
            books[key] = book

        # -------------------------------------------------------------------------
        # 3. Sample Shelves
        # -------------------------------------------------------------------------
        shelves_def = [
            {"user": owner, "name": "Favorites"},
            {"user": owner, "name": "Currently Reading"},
            {"user": owner, "name": "Backend & Tech"},
            {"user": collaborator, "name": "Collab Reading Circle"},
        ]
        shelves = {}
        for s_spec in shelves_def:
            key = (s_spec["user"].id, s_spec["name"])
            shelf = (
                db.query(Shelf)
                .filter(Shelf.user_id == s_spec["user"].id, Shelf.name == s_spec["name"])
                .first()
            )
            if not shelf:
                shelf = Shelf(user_id=s_spec["user"].id, name=s_spec["name"])
                db.add(shelf)
                db.flush()
                stats["shelves_created"] += 1
            else:
                stats["shelves_reused"] += 1
            shelves[key] = shelf

        fav_shelf = shelves[(owner.id, "Favorites")]
        reading_shelf = shelves[(owner.id, "Currently Reading")]
        backend_shelf = shelves[(owner.id, "Backend & Tech")]
        collab_shelf = shelves[(collaborator.id, "Collab Reading Circle")]

        # -------------------------------------------------------------------------
        # 4. ShelfBook Relationships
        # -------------------------------------------------------------------------
        # Favorites: 3 books (Clean Architecture, DDIA, Domain-Driven Design)
        # Currently Reading: 2 books (DDIA, Domain-Driven Design)
        # Backend & Tech: 1 book (Site Reliability Engineering)
        # Collab Reading Circle: 1 book (Refactoring)
        links_def = [
            (fav_shelf, books[(owner.id, "Clean Architecture")]),
            (fav_shelf, books[(owner.id, "Designing Data-Intensive Applications")]),
            (fav_shelf, books[(owner.id, "Domain-Driven Design")]),
            (reading_shelf, books[(owner.id, "Designing Data-Intensive Applications")]),
            (reading_shelf, books[(owner.id, "Domain-Driven Design")]),
            (backend_shelf, books[(owner.id, "Site Reliability Engineering")]),
            (collab_shelf, books[(collaborator.id, "Refactoring")]),
        ]

        for shelf, book in links_def:
            link = (
                db.query(ShelfBook)
                .filter(ShelfBook.shelf_id == shelf.id, ShelfBook.book_id == book.id)
                .first()
            )
            if not link:
                link = ShelfBook(shelf_id=shelf.id, book_id=book.id)
                db.add(link)
                db.flush()
                stats["shelf_links_created"] += 1
            else:
                stats["shelf_links_reused"] += 1

        # -------------------------------------------------------------------------
        # 5. Shelf Sharing (RBAC: Editor and Viewer)
        # -------------------------------------------------------------------------
        shares_def = [
            {"shelf": fav_shelf, "user": collaborator, "role": "editor"},
            {"shelf": backend_shelf, "user": collaborator, "role": "viewer"},
        ]

        for sh in shares_def:
            share = (
                db.query(ShelfShare)
                .filter(ShelfShare.shelf_id == sh["shelf"].id, ShelfShare.user_id == sh["user"].id)
                .first()
            )
            if not share:
                share = ShelfShare(
                    shelf_id=sh["shelf"].id,
                    user_id=sh["user"].id,
                    role=sh["role"],
                )
                db.add(share)
                db.flush()
                stats["shelf_shares_created"] += 1
            else:
                if share.role != sh["role"]:
                    share.role = sh["role"]
                    db.flush()
                stats["shelf_shares_reused"] += 1

        # -------------------------------------------------------------------------
        # 6. Active Peer Lending
        # -------------------------------------------------------------------------
        ddd_book = books[(owner.id, "Domain-Driven Design")]
        active_loan = (
            db.query(Lending)
            .filter(Lending.book_id == ddd_book.id, Lending.is_active == True)
            .first()
        )
        if not active_loan:
            active_loan = Lending(
                book_id=ddd_book.id,
                lender_id=owner.id,
                borrower_id=collaborator.id,
                is_active=True,
                lent_at=now - timedelta(days=3),
            )
            db.add(active_loan)
            db.flush()
            stats["lendings_created"] += 1
        else:
            stats["lendings_reused"] += 1

        # -------------------------------------------------------------------------
        # 7. Idempotent Activity Logs
        # -------------------------------------------------------------------------
        # Seed activity records for key demonstration events
        activities_def = [
            # Book additions
            {
                "user_id": owner.id,
                "action": "book_added",
                "details": {
                    "book_id": str(books[(owner.id, "Clean Architecture")].id),
                    "title": "Clean Architecture",
                    "author": "Robert C. Martin",
                    "status": "finished",
                    "seed_tag": "seed_ca",
                },
                "shelf_id": None,
            },
            {
                "user_id": owner.id,
                "action": "book_added",
                "details": {
                    "book_id": str(books[(owner.id, "Designing Data-Intensive Applications")].id),
                    "title": "Designing Data-Intensive Applications",
                    "author": "Martin Kleppmann",
                    "status": "reading",
                    "seed_tag": "seed_ddia",
                },
                "shelf_id": None,
            },
            {
                "user_id": owner.id,
                "action": "book_added",
                "details": {
                    "book_id": str(books[(owner.id, "The Pragmatic Programmer")].id),
                    "title": "The Pragmatic Programmer",
                    "author": "David Thomas, Andrew Hunt",
                    "status": "want_to_read",
                    "seed_tag": "seed_pragmatic",
                },
                "shelf_id": None,
            },
            {
                "user_id": owner.id,
                "action": "book_added",
                "details": {
                    "book_id": str(books[(owner.id, "Domain-Driven Design")].id),
                    "title": "Domain-Driven Design",
                    "author": "Eric Evans",
                    "status": "reading",
                    "seed_tag": "seed_ddd",
                },
                "shelf_id": None,
            },
            {
                "user_id": owner.id,
                "action": "book_added",
                "details": {
                    "book_id": str(books[(owner.id, "Site Reliability Engineering")].id),
                    "title": "Site Reliability Engineering",
                    "author": "Betsy Beyer, Chris Jones, Niall Murphy",
                    "status": "finished",
                    "seed_tag": "seed_sre",
                },
                "shelf_id": None,
            },
            {
                "user_id": collaborator.id,
                "action": "book_added",
                "details": {
                    "book_id": str(books[(collaborator.id, "Refactoring")].id),
                    "title": "Refactoring",
                    "author": "Martin Fowler",
                    "status": "reading",
                    "seed_tag": "seed_refactoring",
                },
                "shelf_id": None,
            },
            {
                "user_id": collaborator.id,
                "action": "book_added",
                "details": {
                    "book_id": str(books[(collaborator.id, "Patterns of Enterprise Application Architecture")].id),
                    "title": "Patterns of Enterprise Application Architecture",
                    "author": "Martin Fowler",
                    "status": "want_to_read",
                    "seed_tag": "seed_poeaa",
                },
                "shelf_id": None,
            },
            # Shelf shares
            {
                "user_id": owner.id,
                "action": "shelf_shared",
                "details": {
                    "shelf_id": str(fav_shelf.id),
                    "shelf_name": fav_shelf.name,
                    "collaborator_id": str(collaborator.id),
                    "collaborator_email": collaborator.email,
                    "collaborator_name": collaborator.name,
                    "role": "editor",
                    "seed_tag": "seed_share_fav",
                },
                "shelf_id": fav_shelf.id,
            },
            {
                "user_id": owner.id,
                "action": "shelf_shared",
                "details": {
                    "shelf_id": str(backend_shelf.id),
                    "shelf_name": backend_shelf.name,
                    "collaborator_id": str(collaborator.id),
                    "collaborator_email": collaborator.email,
                    "collaborator_name": collaborator.name,
                    "role": "viewer",
                    "seed_tag": "seed_share_backend",
                },
                "shelf_id": backend_shelf.id,
            },
            # Lending
            {
                "user_id": owner.id,
                "action": "book_lent",
                "details": {
                    "book_id": str(ddd_book.id),
                    "book_title": ddd_book.title,
                    "lending_id": str(active_loan.id),
                    "borrower_id": str(collaborator.id),
                    "borrower_name": collaborator.name,
                    "borrower_email": collaborator.email,
                    "seed_tag": "seed_lent_ddd",
                },
                "shelf_id": None,
            },
        ]

        # Fetch existing activities for users
        existing_logs = (
            db.query(ActivityLog)
            .filter(ActivityLog.user_id.in_([owner.id, collaborator.id]))
            .all()
        )
        existing_tags = set()
        for log in existing_logs:
            if log.details and "seed_tag" in log.details:
                existing_tags.add(log.details["seed_tag"])

        for act in activities_def:
            tag = act["details"]["seed_tag"]
            if tag not in existing_tags:
                new_log = ActivityLog(
                    user_id=act["user_id"],
                    action=act["action"],
                    details=act["details"],
                    shelf_id=act["shelf_id"],
                )
                db.add(new_log)
                existing_tags.add(tag)
                stats["activities_created"] += 1
            else:
                stats["activities_reused"] += 1

        owner_email = owner.email
        owner_name = owner.name
        collab_email = collaborator.email
        collab_name = collaborator.name

        db.commit()

    # -------------------------------------------------------------------------
    # CLI Summary Output
    # -------------------------------------------------------------------------
    print("==================================================")
    print("              BookNest Seed Complete              ")
    print("==================================================")
    print("\nDemo users:")
    print(f"  - {owner_email} ({owner_name})")
    print(f"  - {collab_email} ({collab_name})")
    print("\nDemo password:")
    print(f"  - {DEMO_PASSWORD}")
    print("\nSummary of records:")
    print(f"  - Users: {len(users_def)} (created: {stats['users_created']}, reused: {stats['users_reused']})")
    print(f"  - Books: {len(books_def)} (created: {stats['books_created']}, reused: {stats['books_reused']})")
    print(f"  - Shelves: {len(shelves_def)} (created: {stats['shelves_created']}, reused: {stats['shelves_reused']})")
    print(f"  - Shelf links: {len(links_def)} (created: {stats['shelf_links_created']}, reused: {stats['shelf_links_reused']})")
    print(f"  - Shelf shares: {len(shares_def)} (created: {stats['shelf_shares_created']}, reused: {stats['shelf_shares_reused']})")
    print(f"  - Active lending: 1 (created: {stats['lendings_created']}, reused: {stats['lendings_reused']})")
    print(f"  - Activity records: {len(activities_def)} (created: {stats['activities_created']}, reused: {stats['activities_reused']})")
    print("==================================================\n")
    return stats


if __name__ == "__main__":
    seed_database()
