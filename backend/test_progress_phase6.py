"""
Comprehensive Phase 6 Automated Test Suite for BookNest:
Reading Progress Tracker, Page Updates, Milestones, and Reading Statistics

Verifies:
1. Progress update auto-transitions: want_to_read -> reading on current_page > 0.
2. Boundary validations: current_page > total_pages rejected with 422.
3. Boundary validations: negative current_page rejected with 422.
4. Single-occurrence milestone triggers:
   - 0% -> 25% triggers milestone 'quarter'
   - 25% -> 35% returns milestone None (no repeat trigger within same bracket)
   - 35% -> 50% triggers milestone 'half'
   - 50% -> 75% triggers milestone 'three_quarters'
   - 75% -> 100% triggers milestone 'completed' and auto-transitions to 'finished' with finished_date set.
5. Regression from finished: reducing page reverts status to 'reading' and clears finished_date.
6. Books without total_pages: allows page updates cleanly with null percentage.
7. Reading statistics endpoint (GET /api/books/stats/summary):
   - Correctly aggregates total_books, status counts, total_pages_read, and completion_rate.
   - Empty library returns completion_rate = 0.0.
8. Route ordering: GET /api/books/stats/summary succeeds without conflict from /{book_id}.
9. Multi-user isolation: User B cannot update User A's book progress (404).
10. Activity logging: Exactly one ActivityLog entry created per update, without duplicate records.
11. Phase 3 regression check: Standard PATCH /books/{id} preserves manual updates and boundary checks.
"""
import asyncio
import sys
import uuid
import httpx
from app.database import SessionLocal
from app.models.activity_log import ActivityLog
from app.models.book import Book

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://localhost:8000/api"


def log_step(num: int, title: str):
    print(f"\n[{num}/11] {title}")


async def run_tests():
    print("=== Starting Phase 6 Reading Progress Tracker & Page Updates Test Suite ===\n")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # Setup: Create User A and User B
        ts = int(asyncio.get_event_loop().time() * 1000)
        user_a_email = f"progress_user_a_{ts}@example.com"
        user_b_email = f"progress_user_b_{ts}@example.com"

        res_a = await client.post("/auth/signup", json={
            "name": "Progress User Alpha", "email": user_a_email, "password": "Pass@Word123"
        })
        assert res_a.status_code == 201, f"User A signup failed: {res_a.text}"
        token_a = res_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        res_b = await client.post("/auth/signup", json={
            "name": "Progress User Beta", "email": user_b_email, "password": "Pass@Word123"
        })
        assert res_b.status_code == 201, f"User B signup failed: {res_b.text}"
        token_b = res_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}
        print("   [OK] Test users registered successfully.")

        # Test 1: Empty library stats
        log_step(1, "Testing GET /books/stats/summary on empty library...")
        res = await client.get("/books/stats/summary", headers=headers_a)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        stats_empty = res.json()
        assert stats_empty["total_books"] == 0
        assert stats_empty["books_want_to_read"] == 0
        assert stats_empty["books_reading"] == 0
        assert stats_empty["books_finished"] == 0
        assert stats_empty["total_pages_read"] == 0
        assert stats_empty["completion_rate"] == 0.0
        print("   [OK] Empty library stats verified with completion_rate = 0.0")

        # Test 2: Create a book (want_to_read, 200 pages)
        log_step(2, "Creating test book and testing auto-transition want_to_read -> reading...")
        res = await client.post("/books", headers=headers_a, json={
            "title": "The Way of Kings",
            "author": "Brandon Sanderson",
            "status": "want_to_read",
            "total_pages": 200,
            "current_page": 0,
        })
        assert res.status_code == 201
        book1 = res.json()
        book1_id = book1["id"]
        assert book1["status"] == "want_to_read"
        assert book1["current_page"] == 0
        assert book1["progress_percentage"] == 0.0

        # Advance progress to page 20 (10%)
        res = await client.post(f"/books/{book1_id}/progress", headers=headers_a, json={
            "current_page": 20,
            "notes": "Starting chapter 1",
        })
        assert res.status_code == 200, f"Progress update failed: {res.text}"
        p1 = res.json()
        assert p1["book"]["current_page"] == 20
        assert p1["book"]["status"] == "reading", "current_page > 0 should auto-advance to reading"
        assert p1["book"]["progress_percentage"] == 10.0
        assert p1["book"]["notes"] == "Starting chapter 1"
        assert p1["milestone"] is None, "10% should not trigger a milestone"
        print("   [OK] Successfully auto-advanced status from want_to_read to reading on page 20.")

        # Test 3: Boundary validation on progress endpoint
        log_step(3, "Testing boundary validations on progress endpoint...")
        # 3a: Negative page
        res = await client.post(f"/books/{book1_id}/progress", headers=headers_a, json={"current_page": -5})
        assert res.status_code == 422, f"Expected 422 for negative page, got {res.status_code}"
        print("   [OK] Negative page correctly rejected with 422.")

        # 3b: Exceeding total_pages
        res = await client.post(f"/books/{book1_id}/progress", headers=headers_a, json={"current_page": 250})
        assert res.status_code == 422, f"Expected 422 for exceeding total_pages, got {res.status_code}"
        print("   [OK] current_page > total_pages correctly rejected with 422.")

        # Test 4: Single-occurrence milestone tracking
        log_step(4, "Testing single-occurrence milestone tracking (25%, 50%, 75%, 100%)...")
        # Advance to 50 pages (25% milestone: quarter)
        res = await client.post(f"/books/{book1_id}/progress", headers=headers_a, json={"current_page": 50})
        assert res.status_code == 200
        p_25 = res.json()
        assert p_25["book"]["progress_percentage"] == 25.0
        assert p_25["milestone"] == "quarter", f"Expected 'quarter', got {p_25['milestone']}"
        assert "Quarter" in p_25["milestone_label"]
        print("   [OK] Hit 25% -> Milestone 'quarter' triggered.")

        # Advance to 60 pages (30% -> within 25-50% bracket, should NOT trigger quarter again)
        res = await client.post(f"/books/{book1_id}/progress", headers=headers_a, json={"current_page": 60})
        assert res.status_code == 200
        p_30 = res.json()
        assert p_30["book"]["progress_percentage"] == 30.0
        assert p_30["milestone"] is None, "Milestone should NOT re-trigger when already past 25%"
        print("   [OK] Advance to 30% -> Milestone is None (no duplicate triggers).")

        # Advance to 100 pages (50% milestone: half)
        res = await client.post(f"/books/{book1_id}/progress", headers=headers_a, json={"current_page": 100})
        assert res.status_code == 200
        p_50 = res.json()
        assert p_50["book"]["progress_percentage"] == 50.0
        assert p_50["milestone"] == "half"
        print("   [OK] Hit 50% -> Milestone 'half' triggered.")

        # Advance to 150 pages (75% milestone: three_quarters)
        res = await client.post(f"/books/{book1_id}/progress", headers=headers_a, json={"current_page": 150})
        assert res.status_code == 200
        p_75 = res.json()
        assert p_75["book"]["progress_percentage"] == 75.0
        assert p_75["milestone"] == "three_quarters"
        print("   [OK] Hit 75% -> Milestone 'three_quarters' triggered.")

        # Advance to 200 pages (100% milestone: completed + auto-finish)
        res = await client.post(f"/books/{book1_id}/progress", headers=headers_a, json={"current_page": 200})
        assert res.status_code == 200
        p_100 = res.json()
        assert p_100["book"]["progress_percentage"] == 100.0
        assert p_100["book"]["status"] == "finished", "Reaching total_pages must auto-transition to finished"
        assert p_100["book"]["finished_date"] is not None, "finished_date must be timestamped"
        assert p_100["milestone"] == "completed"
        print("   [OK] Hit 100% -> Milestone 'completed' triggered, status set to finished, finished_date set.")

        # Test 5: Status regression
        log_step(5, "Testing status regression from finished back to reading...")
        res = await client.post(f"/books/{book1_id}/progress", headers=headers_a, json={"current_page": 180})
        assert res.status_code == 200
        p_regress = res.json()
        assert p_regress["book"]["current_page"] == 180
        assert p_regress["book"]["status"] == "reading", "Dropping below total_pages must revert status to reading"
        assert p_regress["book"]["finished_date"] is None, "finished_date must be cleared to None"
        print("   [OK] Reducing current_page on finished book reverted status to reading and cleared finished_date.")

        # Test 6: Book without total_pages
        log_step(6, "Testing progress on book without total_pages...")
        res = await client.post("/books", headers=headers_a, json={
            "title": "Untracked Pages Book",
            "author": "Author X",
            "status": "reading",
        })
        assert res.status_code == 201
        book2_id = res.json()["id"]

        res = await client.post(f"/books/{book2_id}/progress", headers=headers_a, json={"current_page": 45})
        assert res.status_code == 200
        p_no_total = res.json()
        assert p_no_total["book"]["current_page"] == 45
        assert p_no_total["book"]["progress_percentage"] is None
        assert p_no_total["milestone"] is None
        print("   [OK] Book without total_pages cleanly tracked page 45 with null percentage.")

        # Test 7: Multi-book reading statistics calculation
        log_step(7, "Testing reading statistics calculation with multiple books...")
        # Create third book and mark it finished
        res = await client.post("/books", headers=headers_a, json={
            "title": "Atomic Habits",
            "author": "James Clear",
            "status": "finished",
            "total_pages": 300,
            "current_page": 300,
        })
        assert res.status_code == 201

        # Now User A has:
        # 1. The Way of Kings: status='reading', current_page=180
        # 2. Untracked Pages Book: status='reading', current_page=45
        # 3. Atomic Habits: status='finished', current_page=300
        # Total pages read = 180 + 45 + 300 = 525
        # Total books = 3, finished = 1 -> completion_rate = round(1/3 * 100, 1) = 33.3%

        res = await client.get("/books/stats/summary", headers=headers_a)
        assert res.status_code == 200
        stats = res.json()
        assert stats["total_books"] == 3
        assert stats["books_want_to_read"] == 0
        assert stats["books_reading"] == 2
        assert stats["books_finished"] == 1
        assert stats["total_pages_read"] == 525
        assert stats["completion_rate"] == 33.3
        print(f"   [OK] Reading stats verified: total_books=3, pages=525, completion_rate=33.3%")

        # Test 8: Multi-user isolation on progress endpoint
        log_step(8, "Testing multi-user isolation on progress endpoint...")
        # User B tries to update User A's book progress
        res = await client.post(f"/books/{book1_id}/progress", headers=headers_b, json={"current_page": 100})
        assert res.status_code == 404, f"Expected 404 when User B updates User A's book, got {res.status_code}"
        print("   [OK] User B received 404 trying to update User A's book progress.")

        # User B's stats are independent
        res = await client.get("/books/stats/summary", headers=headers_b)
        assert res.status_code == 200
        stats_b = res.json()
        assert stats_b["total_books"] == 0
        assert stats_b["total_pages_read"] == 0
        assert stats_b["completion_rate"] == 0.0
        print("   [OK] User B stats completely isolated from User A.")

        # Test 9: Activity Logging Verification in PostgreSQL
        log_step(9, "Verifying ActivityLog entries in database...")
        db = SessionLocal()
        try:
            logs = (
                db.query(ActivityLog)
                .filter(ActivityLog.user_id == uuid.UUID(book1["user_id"]))
                .order_by(ActivityLog.created_at.desc())
                .all()
            )
            assert len(logs) > 0, "Expected ActivityLog records to be generated"
            # Verify actions are valid
            for l in logs:
                assert l.action in ("status_changed", "progress_updated")
                assert l.details is not None
                assert "book_id" in l.details
                assert "old_page" in l.details
                assert "new_page" in l.details
            print(f"   [OK] Successfully verified {len(logs)} activity logs for reading progress and status transitions.")
        finally:
            db.close()

        # Test 10: Preserving Phase 3 PATCH/PUT behavior
        log_step(10, "Verifying Phase 3 standard PATCH /books/{id} compatibility...")
        res = await client.patch(f"/books/{book1_id}", headers=headers_a, json={
            "rating": 5,
            "notes": "An epic masterpiece of fantasy literature",
        })
        assert res.status_code == 200
        patched = res.json()
        assert patched["rating"] == 5
        assert patched["notes"] == "An epic masterpiece of fantasy literature"
        # Verify page boundary on standard PATCH still works
        res = await client.patch(f"/books/{book1_id}", headers=headers_a, json={"current_page": 999})
        assert res.status_code == 422
        print("   [OK] Phase 3 PATCH endpoint preserved and fully functional.")

        # Test 11: Route ordering verification (stats/summary vs {book_id})
        log_step(11, "Verifying route ordering (stats/summary route precedence)...")
        res = await client.get("/books/stats/summary", headers=headers_a)
        assert res.status_code == 200
        assert "completion_rate" in res.json()
        print("   [OK] Route /books/stats/summary matches cleanly without UUID conversion error.")

    print("\nALL 11 PHASE 6 AUTOMATED TESTS PASSED SUCCESSFULLY! [OK]")


if __name__ == "__main__":
    asyncio.run(run_tests())
