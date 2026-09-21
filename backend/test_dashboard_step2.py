"""
Comprehensive Test Suite for BookNest Step 2: Dashboard Requirement #32
Dedicated Dashboard Summary Endpoint (GET /api/dashboard/summary)

Verifies:
1. Authentication requirement: unauthenticated request returns 401 Unauthorized.
2. Empty/no-data case: fresh user gets 0 counts, 0.0 average rating, null top shelf.
3. Status counts: books correctly categorized into want_to_read, reading, finished.
4. Finished-this-year logic: only books finished in the current calendar year are counted.
5. Average rating: correctly calculated from rated books; unrated books excluded.
6. Top shelf calculation: owned shelf with highest book count returned.
7. Deterministic tie-breaking: identical counts resolve deterministically (name alphabetical ascending).
8. Empty shelves / zero books on shelves: returns null top shelf.
9. Active lending: user's books currently lent out are counted.
10. Returned lending: returned loans are excluded from currently lent out count.
11. Shared-with-me shelf count: collaborative shared shelves counted for invitee.
12. Own shelf excluded: user's own shelves are never counted in shared-with-me.
13. Strict multi-user isolation: User A's metrics never leak into User B's dashboard.
"""
import asyncio
import sys
import uuid
from datetime import datetime, timezone, timedelta
import httpx

from app.database import SessionLocal
from app.models.book import Book
from app.models.shelf import Shelf
from app.models.shelf_book import ShelfBook
from app.models.shelf_share import ShelfShare
from app.models.lending import Lending

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://localhost:8000/api"


def log_step(num: int, title: str):
    print(f"\n[{num}/12] {title}")


async def run_tests():
    print("=== Starting BookNest Step 2 Dashboard Requirement #32 Test Suite ===\n")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # Step 1: Verify Authentication Requirement
        log_step(1, "Testing authentication requirement on GET /dashboard/summary...")
        res_unauth = await client.get("/dashboard/summary")
        assert res_unauth.status_code == 401, f"Expected 401, got {res_unauth.status_code}: {res_unauth.text}"
        print("   [OK] Unauthenticated request correctly rejected with 401 Unauthorized.")

        # Setup: Create User A and User B
        ts = int(asyncio.get_event_loop().time() * 1000)
        user_a_email = f"dash_user_a_{ts}@example.com"
        user_b_email = f"dash_user_b_{ts}@example.com"

        res_a = await client.post("/auth/signup", json={
            "name": "Dashboard User Alpha", "email": user_a_email, "password": "Pass@Word123"
        })
        assert res_a.status_code == 201, f"User A signup failed: {res_a.text}"
        token_a = res_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        res_b = await client.post("/auth/signup", json={
            "name": "Dashboard User Beta", "email": user_b_email, "password": "Pass@Word123"
        })
        assert res_b.status_code == 201, f"User B signup failed: {res_b.text}"
        token_b = res_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}
        print("   [OK] Test users Alpha and Beta registered.")

        # Step 2: Empty / No-Data Case
        log_step(2, "Testing empty/no-data dashboard summary on fresh account...")
        res = await client.get("/dashboard/summary", headers=headers_a)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        summary = res.json()

        assert summary["status_counts"]["want_to_read"] == 0
        assert summary["status_counts"]["reading"] == 0
        assert summary["status_counts"]["finished"] == 0
        assert summary["books_finished_this_year"] == 0
        assert summary["average_rating"] == 0.0
        assert summary["shelf_with_most_books"] is None
        assert summary["books_currently_lent_out"] == 0
        assert summary["shelves_shared_with_me"] == 0
        print("   [OK] Fresh account returns zero counts, 0.0 rating, and null top shelf.")

        # Step 3: Status Counts & Average Rating
        log_step(3, "Testing status counts and average rating calculation...")
        # Create Book 1: want_to_read, unrated
        res_b1 = await client.post("/books", headers=headers_a, json={
            "title": "Clean Code", "author": "Robert C. Martin", "status": "want_to_read"
        })
        assert res_b1.status_code == 201
        book1_id = res_b1.json()["id"]

        # Create Book 2: reading, rating=4
        res_b2 = await client.post("/books", headers=headers_a, json={
            "title": "Refactoring", "author": "Martin Fowler", "status": "reading",
            "total_pages": 400, "current_page": 100, "rating": 4
        })
        assert res_b2.status_code == 201
        book2_id = res_b2.json()["id"]

        # Create Book 3: finished, rating=5 (finished today in current calendar year)
        res_b3 = await client.post("/books", headers=headers_a, json={
            "title": "Design Patterns", "author": "Gang of Four", "status": "finished",
            "total_pages": 300, "rating": 5
        })
        assert res_b3.status_code == 201
        book3_id = res_b3.json()["id"]

        res = await client.get("/dashboard/summary", headers=headers_a)
        assert res.status_code == 200
        summary = res.json()
        assert summary["status_counts"]["want_to_read"] == 1
        assert summary["status_counts"]["reading"] == 1
        assert summary["status_counts"]["finished"] == 1
        # Average rating: (4 + 5) / 2 = 4.5; book 1 is unrated and must not skew average
        assert summary["average_rating"] == 4.5
        assert summary["books_finished_this_year"] == 1
        print("   [OK] Status counts (1, 1, 1), average rating (4.5), and finished this year (1) verified.")

        # Step 4: Finished-This-Year Logic (Past Calendar Year Excluded)
        log_step(4, "Testing finished-this-year calendar year filtering...")
        # Create Book 4: finished, but with finished_date in previous year
        res_b4 = await client.post("/books", headers=headers_a, json={
            "title": "Old Book", "author": "Ancient Author", "status": "finished",
            "total_pages": 200, "rating": 3
        })
        assert res_b4.status_code == 201
        book4_id = res_b4.json()["id"]

        # Directly update Book 4 finished_date in DB to 2022
        with SessionLocal() as db:
            past_date = datetime(2022, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
            db.query(Book).filter(Book.id == uuid.UUID(book4_id)).update({"finished_date": past_date})
            db.commit()

        res = await client.get("/dashboard/summary", headers=headers_a)
        summary = res.json()
        # Finished count is 2, but finished_this_year must strictly remain 1!
        assert summary["status_counts"]["finished"] == 2
        assert summary["books_finished_this_year"] == 1
        print("   [OK] Book finished in 2022 excluded from books_finished_this_year.")

        # Create Book 5: finished today -> finished_this_year increments to 2
        res_b5 = await client.post("/books", headers=headers_a, json={
            "title": "Current Year Book", "author": "Modern Author", "status": "finished",
            "total_pages": 150
        })
        assert res_b5.status_code == 201
        res = await client.get("/dashboard/summary", headers=headers_a)
        assert res.json()["books_finished_this_year"] == 2
        print("   [OK] New book finished today increments books_finished_this_year to 2.")

        # Step 5: Empty Shelves (Shelves exist but have 0 books -> top shelf is null)
        log_step(5, "Testing top shelf with empty shelves...")
        res_s1 = await client.post("/shelves", headers=headers_a, json={"name": "Empty Shelf"})
        assert res_s1.status_code == 201
        shelf1_id = res_s1.json()["id"]

        res = await client.get("/dashboard/summary", headers=headers_a)
        assert res.json()["shelf_with_most_books"] is None
        print("   [OK] Shelf with 0 books returns null shelf_with_most_books.")

        # Step 6: Top Shelf with Books
        log_step(6, "Testing top shelf calculation with books assigned...")
        res_s2 = await client.post("/shelves", headers=headers_a, json={"name": "Tech Books"})
        assert res_s2.status_code == 201
        shelf2_id = res_s2.json()["id"]

        # Add Book 1 and Book 2 to Tech Books (count = 2)
        await client.post(f"/shelves/{shelf2_id}/books", headers=headers_a, json={"book_id": book1_id})
        await client.post(f"/shelves/{shelf2_id}/books", headers=headers_a, json={"book_id": book2_id})

        res = await client.get("/dashboard/summary", headers=headers_a)
        top_shelf = res.json()["shelf_with_most_books"]
        assert top_shelf is not None
        assert top_shelf["id"] == shelf2_id
        assert top_shelf["name"] == "Tech Books"
        assert top_shelf["book_count"] == 2
        print("   [OK] Tech Books identified as top shelf with book_count = 2.")

        # Step 7: Deterministic Tie-Breaking
        log_step(7, "Testing deterministic tie-breaking for shelves with identical book counts...")
        # Create Shelf "A-Shelf" and "Z-Shelf", add 3 books to each
        res_sa = await client.post("/shelves", headers=headers_a, json={"name": "A-Shelf"})
        shelf_a_id = res_sa.json()["id"]
        res_sz = await client.post("/shelves", headers=headers_a, json={"name": "Z-Shelf"})
        shelf_z_id = res_sz.json()["id"]

        # Add 3 books to Z-Shelf first
        await client.post(f"/shelves/{shelf_z_id}/books", headers=headers_a, json={"book_id": book1_id})
        await client.post(f"/shelves/{shelf_z_id}/books", headers=headers_a, json={"book_id": book2_id})
        await client.post(f"/shelves/{shelf_z_id}/books", headers=headers_a, json={"book_id": book3_id})

        # Add 3 books to A-Shelf
        await client.post(f"/shelves/{shelf_a_id}/books", headers=headers_a, json={"book_id": book1_id})
        await client.post(f"/shelves/{shelf_a_id}/books", headers=headers_a, json={"book_id": book2_id})
        await client.post(f"/shelves/{shelf_a_id}/books", headers=headers_a, json={"book_id": book3_id})

        res = await client.get("/dashboard/summary", headers=headers_a)
        top_shelf = res.json()["shelf_with_most_books"]
        assert top_shelf["book_count"] == 3
        # Deterministic tie-breaking orders by name ASC: "A-Shelf" wins over "Z-Shelf"
        assert top_shelf["name"] == "A-Shelf"
        assert top_shelf["id"] == shelf_a_id
        print("   [OK] Deterministic tie-breaking correctly selected 'A-Shelf' over 'Z-Shelf'.")

        # Step 8: Active Lending Count
        log_step(8, "Testing books_currently_lent_out with active peer loan...")
        res_lend = await client.post("/lending", headers=headers_a, json={
            "book_id": book1_id,
            "borrower_email": user_b_email,
        })
        assert res_lend.status_code == 201
        lending_id = res_lend.json()["id"]

        res = await client.get("/dashboard/summary", headers=headers_a)
        assert res.json()["books_currently_lent_out"] == 1
        print("   [OK] Active loan correctly reflected in books_currently_lent_out = 1.")

        # Step 9: Returned Lending Excluded
        log_step(9, "Testing returned lending is excluded from books_currently_lent_out...")
        res_return = await client.post(f"/lending/{lending_id}/return", headers=headers_a)
        assert res_return.status_code == 200

        res = await client.get("/dashboard/summary", headers=headers_a)
        assert res.json()["books_currently_lent_out"] == 0
        print("   [OK] Returned loan successfully decremented books_currently_lent_out to 0.")

        # Step 10: Shelves Shared With Me
        log_step(10, "Testing shelves_shared_with_me count for collaborator...")
        # User B creates a shelf and shares it with User A
        res_sb = await client.post("/shelves", headers=headers_b, json={"name": "Beta Shared Club"})
        assert res_sb.status_code == 201
        beta_shelf_id = res_sb.json()["id"]

        res_share = await client.post(f"/shelves/{beta_shelf_id}/shares", headers=headers_b, json={
            "email": user_a_email,
            "role": "editor",
        })
        assert res_share.status_code == 201

        res = await client.get("/dashboard/summary", headers=headers_a)
        assert res.json()["shelves_shared_with_me"] == 1
        print("   [OK] shelves_shared_with_me correctly shows 1 collaborative shelf for User A.")

        # Step 11: Own Shelves Excluded From Shared-With-Me
        log_step(11, "Testing user's own shelves are excluded from shelves_shared_with_me...")
        # User A owns 4 shelves, but shelves_shared_with_me must be strictly 1
        # User B owns 1 shelf and has 0 shelves shared with them
        res_b_summary = await client.get("/dashboard/summary", headers=headers_b)
        assert res_b_summary.json()["shelves_shared_with_me"] == 0
        print("   [OK] Owner does not have their own shared shelf counted in shelves_shared_with_me.")

        # Step 12: Multi-User Isolation
        log_step(12, "Verifying strict multi-user isolation on dashboard metrics...")
        summary_b = res_b_summary.json()
        assert summary_b["status_counts"]["want_to_read"] == 0
        assert summary_b["status_counts"]["reading"] == 0
        assert summary_b["status_counts"]["finished"] == 0
        assert summary_b["books_finished_this_year"] == 0
        assert summary_b["average_rating"] == 0.0
        assert summary_b["shelf_with_most_books"] is None
        assert summary_b["books_currently_lent_out"] == 0
        assert summary_b["shelves_shared_with_me"] == 0
        print("   [OK] User B dashboard is completely isolated from User A.")

    print("\n=================================================================")
    print("  ALL 12 DASHBOARD REQUIREMENT #32 TESTS PASSED SUCCESSFULLY!  ")
    print("=================================================================\n")


if __name__ == "__main__":
    asyncio.run(run_tests())
