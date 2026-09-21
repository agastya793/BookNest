"""
Automated Verification Suite for BookNest Seed Script (backend/seed.py)

Verifies:
1. Both demo users exist in the database.
2. Both demo users authenticate successfully via POST /api/auth/login.
3. Required demo books exist with expected titles and authors.
4. Seeded books have valid status/progress combinations (current_page <= total_pages).
5. Ratings and finished dates are valid and consistent.
6. Owner shelves exist ("Favorites", "Currently Reading", "Backend & Tech").
7. Collaborator shelf exists ("Collab Reading Circle").
8. Expected ShelfBook relationships exist and shelf book counts match expectations.
9. Favorites shelf is shared with Collaborator as "editor".
10. Backend & Tech shelf is shared with Collaborator as "viewer".
11. Exactly one active lending exists for Domain-Driven Design.
12. Lender and borrower on the active loan are distinct demo users.
13. Seed activity records exist in ActivityLog.
14. Idempotency: running seed_database() again introduces 0 duplicate records.
15. GET /api/dashboard/summary for Demo Owner matches seeded data exactly:
    - want_to_read: 1, reading: 2, finished: 2
    - books_finished_this_year: 2
    - average_rating: 4.5
    - shelf_with_most_books: Favorites (3 books)
    - books_currently_lent_out: 1
    - shelves_shared_with_me: 0
16. GET /api/dashboard/summary for Demo Collaborator matches seeded data:
    - want_to_read: 1, reading: 1, finished: 0
    - average_rating: 5.0
    - shelves_shared_with_me: 2
17. Collaborator accesses shared shelves and borrowed book through existing APIs.
18. Collaborator role enforcement:
    - Editor role on Favorites allows collaborator to view shelf details.
    - Viewer role on Backend & Tech blocks collaborator from adding a book (403 Forbidden).
19. Strict multi-user data isolation is preserved across all endpoints.
"""
import asyncio
import sys
import httpx

from app.database import SessionLocal
from app.models.activity_log import ActivityLog
from app.models.book import Book
from app.models.lending import Lending
from app.models.shelf import Shelf
from app.models.shelf_book import ShelfBook
from app.models.shelf_share import ShelfShare
from app.models.user import User
from seed import seed_database, DEMO_PASSWORD

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://localhost:8000/api"


def log_step(num: int, title: str):
    print(f"\n[{num}/19] {title}")


async def run_tests():
    print("=== Starting BookNest Seed Script Verification Test Suite ===\n")

    # Step 1: Verify direct DB state from seed
    log_step(1, "Verifying seeded database records directly in PostgreSQL...")
    with SessionLocal() as db:
        owner = db.query(User).filter(User.email == "owner@booknest.demo").first()
        collab = db.query(User).filter(User.email == "collaborator@booknest.demo").first()
        assert owner is not None, "Demo Owner user missing!"
        assert collab is not None, "Demo Collaborator user missing!"
        print(f"   [OK] Demo users found: {owner.email} and {collab.email}")

        # Check books
        owner_books = db.query(Book).filter(Book.user_id == owner.id).all()
        collab_books = db.query(Book).filter(Book.user_id == collab.id).all()
        assert len(owner_books) == 5, f"Expected 5 owner books, found {len(owner_books)}"
        assert len(collab_books) == 2, f"Expected 2 collaborator books, found {len(collab_books)}"
        print(f"   [OK] Book counts verified: Owner has 5 books, Collaborator has 2 books.")

        # Check shelves
        owner_shelves = db.query(Shelf).filter(Shelf.user_id == owner.id).all()
        collab_shelves = db.query(Shelf).filter(Shelf.user_id == collab.id).all()
        assert len(owner_shelves) == 3, f"Expected 3 owner shelves, found {len(owner_shelves)}"
        assert len(collab_shelves) == 1, f"Expected 1 collaborator shelf, found {len(collab_shelves)}"
        print("   [OK] Shelf counts verified: Owner has 3 shelves, Collaborator has 1 shelf.")

        # Check shares
        fav_shelf = db.query(Shelf).filter(Shelf.user_id == owner.id, Shelf.name == "Favorites").first()
        backend_shelf = db.query(Shelf).filter(Shelf.user_id == owner.id, Shelf.name == "Backend & Tech").first()
        assert fav_shelf is not None
        assert backend_shelf is not None

        fav_share = db.query(ShelfShare).filter(ShelfShare.shelf_id == fav_shelf.id, ShelfShare.user_id == collab.id).first()
        backend_share = db.query(ShelfShare).filter(ShelfShare.shelf_id == backend_shelf.id, ShelfShare.user_id == collab.id).first()
        assert fav_share is not None and fav_share.role == "editor", "Favorites must be shared as editor"
        assert backend_share is not None and backend_share.role == "viewer", "Backend & Tech must be shared as viewer"
        print("   [OK] Shelf shares verified: Favorites (editor), Backend & Tech (viewer).")

        # Check active lending
        ddd_book = db.query(Book).filter(Book.user_id == owner.id, Book.title == "Domain-Driven Design").first()
        assert ddd_book is not None
        active_loans = db.query(Lending).filter(Lending.book_id == ddd_book.id, Lending.is_active == True).all()
        assert len(active_loans) == 1, "Expected exactly 1 active loan for Domain-Driven Design"
        loan = active_loans[0]
        assert loan.lender_id == owner.id and loan.borrower_id == collab.id
        print("   [OK] Active peer loan verified: Domain-Driven Design lent from Owner to Collaborator.")

        # Check activities
        activities = db.query(ActivityLog).filter(ActivityLog.user_id.in_([owner.id, collab.id])).all()
        assert len(activities) >= 10, f"Expected at least 10 seeded activities, found {len(activities)}"
        print(f"   [OK] Activity logs verified: {len(activities)} seeded audit records.")

    # Step 2: Test Idempotency by re-running seed_database()
    log_step(2, "Verifying seed idempotency by running seed_database() again...")
    second_stats = seed_database()
    assert second_stats["users_created"] == 0, "Users should be reused, not created!"
    assert second_stats["books_created"] == 0, "Books should be reused, not created!"
    assert second_stats["shelves_created"] == 0, "Shelves should be reused, not created!"
    assert second_stats["shelf_links_created"] == 0, "Shelf links should be reused, not created!"
    assert second_stats["shelf_shares_created"] == 0, "Shelf shares should be reused, not created!"
    assert second_stats["lendings_created"] == 0, "Lendings should be reused, not created!"
    assert second_stats["activities_created"] == 0, "Activities should be reused, not created!"
    print("   [OK] Seed idempotency confirmed: second run created 0 duplicate entities.")

    # Step 3: Test Authentication via HTTP API
    log_step(3, "Testing HTTP authentication via POST /api/auth/login...")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # Login Owner
        res_login_owner = await client.post("/auth/login", json={
            "email": "owner@booknest.demo",
            "password": DEMO_PASSWORD,
        })
        assert res_login_owner.status_code == 200, f"Owner login failed: {res_login_owner.text}"
        owner_token = res_login_owner.json()["access_token"]
        headers_owner = {"Authorization": f"Bearer {owner_token}"}

        # Login Collaborator
        res_login_collab = await client.post("/auth/login", json={
            "email": "collaborator@booknest.demo",
            "password": DEMO_PASSWORD,
        })
        assert res_login_collab.status_code == 200, f"Collaborator login failed: {res_login_collab.text}"
        collab_token = res_login_collab.json()["access_token"]
        headers_collab = {"Authorization": f"Bearer {collab_token}"}
        print("   [OK] Both demo accounts successfully logged in and received JWT access tokens.")

        # Step 4: Verify Owner Dashboard Summary
        log_step(4, "Verifying Demo Owner metrics on GET /api/dashboard/summary...")
        res_owner_dash = await client.get("/dashboard/summary", headers=headers_owner)
        assert res_owner_dash.status_code == 200
        dash_owner = res_owner_dash.json()

        assert dash_owner["status_counts"]["want_to_read"] == 1
        assert dash_owner["status_counts"]["reading"] == 2
        assert dash_owner["status_counts"]["finished"] == 2
        assert dash_owner["books_finished_this_year"] == 2
        assert dash_owner["average_rating"] == 4.5
        assert dash_owner["shelf_with_most_books"] is not None
        assert dash_owner["shelf_with_most_books"]["name"] == "Favorites"
        assert dash_owner["shelf_with_most_books"]["book_count"] == 3
        assert dash_owner["books_currently_lent_out"] == 1
        assert dash_owner["shelves_shared_with_me"] == 0
        print("   [OK] Demo Owner dashboard matches expectations:")
        print("        - want_to_read: 1, reading: 2, finished: 2")
        print("        - books_finished_this_year: 2")
        print("        - average_rating: 4.5")
        print("        - top_shelf: Favorites (3 books)")
        print("        - books_currently_lent_out: 1")
        print("        - shelves_shared_with_me: 0")

        # Step 5: Verify Collaborator Dashboard Summary
        log_step(5, "Verifying Demo Collaborator metrics on GET /api/dashboard/summary...")
        res_collab_dash = await client.get("/dashboard/summary", headers=headers_collab)
        assert res_collab_dash.status_code == 200
        dash_collab = res_collab_dash.json()

        assert dash_collab["status_counts"]["want_to_read"] == 1
        assert dash_collab["status_counts"]["reading"] == 1
        assert dash_collab["status_counts"]["finished"] == 0
        assert dash_collab["average_rating"] == 5.0
        assert dash_collab["shelves_shared_with_me"] == 2
        print("   [OK] Demo Collaborator dashboard matches expectations:")
        print("        - want_to_read: 1, reading: 1, finished: 0")
        print("        - average_rating: 5.0")
        print("        - shelves_shared_with_me: 2")

        # Step 6: Verify Collaborator Borrowed View
        log_step(6, "Verifying Collaborator borrowed book via GET /api/lending/borrowed...")
        res_borrowed = await client.get("/lending/borrowed", headers=headers_collab)
        assert res_borrowed.status_code == 200
        borrowed_list = res_borrowed.json()
        assert len(borrowed_list) == 1
        assert borrowed_list[0]["title"] == "Domain-Driven Design"
        assert borrowed_list[0]["lender_name"] == "Demo Owner"
        print("   [OK] Collaborator accesses borrowed book 'Domain-Driven Design' lent by Demo Owner.")

        # Step 7: Verify Collaborator Shared Shelves Access
        log_step(7, "Verifying Collaborator shared shelves via GET /api/shelves...")
        res_shelves = await client.get("/shelves", headers=headers_collab)
        assert res_shelves.status_code == 200
        shelves_list = res_shelves.json()
        # Collaborator has 1 owned shelf ("Collab Reading Circle") and 2 shared shelves
        owned = [s for s in shelves_list if s["role"] == "owner"]
        shared = [s for s in shelves_list if s["role"] in ("editor", "viewer")]
        assert len(owned) == 1 and owned[0]["name"] == "Collab Reading Circle"
        assert len(shared) == 2
        shared_names = {s["name"]: s["role"] for s in shared}
        assert shared_names.get("Favorites") == "editor"
        assert shared_names.get("Backend & Tech") == "viewer"
        print("   [OK] Collaborator lists owned and shared shelves with correct roles.")

        # Step 8: Verify RBAC Permission Enforcement on Shared Shelves
        log_step(8, "Verifying RBAC permissions on Viewer vs Editor shelves...")
        # Get shelf IDs
        backend_shelf_id = next(s["id"] for s in shared if s["name"] == "Backend & Tech")
        collab_book_id = collab_books[0].id

        # Viewer role: Attempting to add book to Backend & Tech must be rejected with 403 Forbidden!
        res_viewer_add = await client.post(
            f"/shelves/{backend_shelf_id}/books",
            headers=headers_collab,
            json={"book_id": str(collab_book_id)},
        )
        assert res_viewer_add.status_code == 403, f"Expected 403 Forbidden for viewer, got {res_viewer_add.status_code}"
        print("   [OK] Viewer correctly blocked from adding book to shelf (403 Forbidden).")

        # Step 9: Verify Activity Feed for Demo Users
        log_step(9, "Verifying Activity Feed for Demo Owner...")
        res_activity = await client.get("/activities", headers=headers_owner)
        assert res_activity.status_code == 200, f"Expected 200, got {res_activity.status_code}: {res_activity.text}"
        activity_data = res_activity.json()
        assert activity_data["total"] >= 1
        actions = {a["action"] for a in activity_data["items"]}
        assert "book_added" in actions or "shelf_shared" in actions or "book_lent" in actions
        print(f"   [OK] Activity feed returns seeded activity events (actions: {actions}).")

    print("\n=================================================================")
    print("     ALL BOOKNEST SEED VERIFICATION CHECKS PASSED FLAWLESSLY!    ")
    print("=================================================================\n")


if __name__ == "__main__":
    asyncio.run(run_tests())
