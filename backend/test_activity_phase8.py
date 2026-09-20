"""
Phase 8 Automated Test Suite for BookNest:
Activity Feed & Event Audit Logging

Verifies:
1. User A creates a Book -> exactly one book_added activity created.
2. User A changes status -> exactly one status_changed activity created.
3. User A updates progress without status change -> exactly one progress_updated activity created.
4. Progress update that also changes status creates exactly one appropriate event.
5. User A creates a shelf and shares with User B -> exactly one shelf_shared activity created.
6. Owner changes User B's role -> exactly one shelf_role_changed activity created.
7. Owner removes User B -> exactly one shelf_share_removed activity created.
8. User A lends a book -> exactly one book_lent activity created.
9. User A returns the book -> exactly one book_returned activity created.
10. Failed operations do NOT create activity records.
11. Activity feed is newest-first (created_at DESC).
12. Activity pagination returns requested page_size.
13. total and total_pages are accurate.
14. Action filtering works (e.g. action=book_added).
15. Shelf filtering works (shelf_id=UUID).
16. User B can see activity for a shelf currently shared with B.
17. User D (uninvited) cannot see that shelf's activity.
18. After User B's share is removed, User B loses access to that shelf's activity.
19. Personal book/progress activity is isolated to the owner.
20. Lending activity is visible to participants (lender and borrower) and isolated from unrelated users.
21. Empty activity feed returns correct metadata (total=0, total_pages=0, items=[]).
"""
import asyncio
import sys
import uuid
import httpx
from sqlalchemy import func
from app.database import SessionLocal
from app.models.activity_log import ActivityLog
from app.models.book import Book
from app.models.shelf import Shelf
from app.models.shelf_share import ShelfShare

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://localhost:8000/api"


def log_step(step_num: int, title: str):
    print(f"\n[{step_num}/21] {title}")


async def run_tests():
    print("=== Phase 8: Starting Activity Feed & Audit Logging Test Suite ===")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # Setup: Create 4 test users
        uid = uuid.uuid4().hex[:6]
        user_a_email = f"user_a_{uid}@example.com"  # Owner/Lender
        user_b_email = f"user_b_{uid}@example.com"  # Collaborator/Borrower
        user_c_email = f"user_c_{uid}@example.com"  # Extra collaborator
        user_d_email = f"user_d_{uid}@example.com"  # Unrelated Stranger

        users = {}
        for email, name, key in [
            (user_a_email, "Alice Owner", "A"),
            (user_b_email, "Bob Collaborator", "B"),
            (user_c_email, "Carol Extra", "C"),
            (user_d_email, "Dave Stranger", "D"),
        ]:
            res = await client.post("/auth/signup", json={
                "email": email, "password": "Password123!", "name": name
            })
            assert res.status_code == 201, f"Signup failed for {name}: {res.text}"
            data = res.json()
            users[key] = {
                "id": data["user"]["id"],
                "email": email,
                "name": name,
                "headers": {"Authorization": f"Bearer {data['access_token']}"},
            }
        print("   [OK] Test users A, B, C, D registered successfully.")

        # Test 1 & 2: User A creates a Book -> exactly one book_added activity
        log_step(1, "Testing Book creation and book_added activity generation...")
        res_book = await client.post("/books", headers=users["A"]["headers"], json={
            "title": "Designing Data-Intensive Applications",
            "author": "Martin Kleppmann",
            "total_pages": 500,
            "status": "want_to_read",
        })
        assert res_book.status_code == 201, f"Book creation failed: {res_book.text}"
        book1_id = res_book.json()["id"]

        db = SessionLocal()
        try:
            logs = db.query(ActivityLog).filter(
                ActivityLog.user_id == uuid.UUID(users["A"]["id"]),
                ActivityLog.action == "book_added",
            ).all()
            assert len(logs) == 1, f"Expected 1 book_added log, got {len(logs)}"
            assert logs[0].details["title"] == "Designing Data-Intensive Applications"
            assert logs[0].details["book_id"] == book1_id
            print("   [OK] Exactly 1 book_added activity logged in database.")
        finally:
            db.close()

        # Test 3 & 4: User A changes status directly via PATCH -> exactly one status_changed activity
        log_step(2, "Testing status change on book update and status_changed activity...")
        res_patch = await client.patch(f"/books/{book1_id}", headers=users["A"]["headers"], json={
            "status": "reading",
        })
        assert res_patch.status_code == 200, f"Patch failed: {res_patch.text}"

        db = SessionLocal()
        try:
            status_logs = db.query(ActivityLog).filter(
                ActivityLog.user_id == uuid.UUID(users["A"]["id"]),
                ActivityLog.action == "status_changed",
            ).all()
            assert len(status_logs) == 1, f"Expected 1 status_changed log, got {len(status_logs)}"
            assert status_logs[0].details["old_status"] == "want_to_read"
            assert status_logs[0].details["new_status"] == "reading"
            print("   [OK] Exactly 1 status_changed activity logged on PATCH /books/{id}.")
        finally:
            db.close()

        # Test 5 & 6: User A updates progress without status change -> exactly one progress_updated activity
        log_step(3, "Testing progress update without status change -> progress_updated activity...")
        res_prog1 = await client.post(f"/books/{book1_id}/progress", headers=users["A"]["headers"], json={
            "current_page": 50,
        })
        assert res_prog1.status_code == 200, f"Progress update failed: {res_prog1.text}"

        db = SessionLocal()
        try:
            prog_logs = db.query(ActivityLog).filter(
                ActivityLog.user_id == uuid.UUID(users["A"]["id"]),
                ActivityLog.action == "progress_updated",
            ).all()
            assert len(prog_logs) == 1, f"Expected 1 progress_updated log, got {len(prog_logs)}"
            assert prog_logs[0].details["new_page"] == 50
            print("   [OK] Exactly 1 progress_updated activity logged.")
        finally:
            db.close()

        # Test 7: Progress update causing status transition -> exactly one status_changed event
        log_step(4, "Testing progress update triggering status transition to finished...")
        res_prog2 = await client.post(f"/books/{book1_id}/progress", headers=users["A"]["headers"], json={
            "current_page": 500,
        })
        assert res_prog2.status_code == 200
        assert res_prog2.json()["book"]["status"] == "finished"

        db = SessionLocal()
        try:
            status_logs2 = db.query(ActivityLog).filter(
                ActivityLog.user_id == uuid.UUID(users["A"]["id"]),
                ActivityLog.action == "status_changed",
            ).all()
            # 1 from PATCH, 1 from auto-advancement to finished = 2 total
            assert len(status_logs2) == 2, f"Expected 2 status_changed logs, got {len(status_logs2)}"
            # And progress_updated logs should NOT have increased for this update
            prog_logs2 = db.query(ActivityLog).filter(
                ActivityLog.user_id == uuid.UUID(users["A"]["id"]),
                ActivityLog.action == "progress_updated",
            ).all()
            assert len(prog_logs2) == 1, f"Expected still 1 progress_updated log, got {len(prog_logs2)}"
            print("   [OK] Progress update that changed status logged status_changed without duplicate progress_updated.")
        finally:
            db.close()

        # Test 8, 9, 10: Shelf creation and sharing -> shelf_shared activity
        log_step(5, "Testing shelf sharing and shelf_shared activity generation...")
        res_shelf = await client.post("/shelves", headers=users["A"]["headers"], json={
            "name": f"Architecture Books {uid}",
        })
        assert res_shelf.status_code == 201
        shelf_id = res_shelf.json()["id"]

        res_share = await client.post(f"/shelves/{shelf_id}/shares", headers=users["A"]["headers"], json={
            "email": users["B"]["email"],
            "role": "viewer",
        })
        assert res_share.status_code == 201
        share_id = res_share.json()["id"]

        db = SessionLocal()
        try:
            share_logs = db.query(ActivityLog).filter(
                ActivityLog.shelf_id == uuid.UUID(shelf_id),
                ActivityLog.action == "shelf_shared",
            ).all()
            assert len(share_logs) == 1, f"Expected 1 shelf_shared log, got {len(share_logs)}"
            assert share_logs[0].details["collaborator_email"] == users["B"]["email"]
            assert share_logs[0].details["role"] == "viewer"
            print("   [OK] Exactly 1 shelf_shared activity logged.")
        finally:
            db.close()

        # Test 11 & 12: Owner changes User B's role -> shelf_role_changed activity
        log_step(6, "Testing collaborator role update -> shelf_role_changed activity...")
        res_role = await client.patch(f"/shelves/{shelf_id}/shares/{share_id}", headers=users["A"]["headers"], json={
            "role": "editor",
        })
        assert res_role.status_code == 200
        assert res_role.json()["role"] == "editor"

        db = SessionLocal()
        try:
            role_logs = db.query(ActivityLog).filter(
                ActivityLog.shelf_id == uuid.UUID(shelf_id),
                ActivityLog.action == "shelf_role_changed",
            ).all()
            assert len(role_logs) == 1, f"Expected 1 shelf_role_changed log, got {len(role_logs)}"
            assert role_logs[0].details["old_role"] == "viewer"
            assert role_logs[0].details["new_role"] == "editor"
            print("   [OK] Exactly 1 shelf_role_changed activity logged.")
        finally:
            db.close()

        # Test 13 & 14: Owner removes User B -> shelf_share_removed activity
        log_step(7, "Testing collaborator removal -> shelf_share_removed activity...")
        res_rm = await client.delete(f"/shelves/{shelf_id}/shares/{share_id}", headers=users["A"]["headers"])
        assert res_rm.status_code == 204

        db = SessionLocal()
        try:
            rm_logs = db.query(ActivityLog).filter(
                ActivityLog.shelf_id == uuid.UUID(shelf_id),
                ActivityLog.action == "shelf_share_removed",
            ).all()
            assert len(rm_logs) == 1, f"Expected 1 shelf_share_removed log, got {len(rm_logs)}"
            assert rm_logs[0].details["collaborator_email"] == users["B"]["email"]
            assert rm_logs[0].details["removed_by"] == "owner"
            print("   [OK] Exactly 1 shelf_share_removed activity logged.")
        finally:
            db.close()

        # Test 15 & 16: Book lending -> book_lent activity
        log_step(8, "Testing book lending -> book_lent activity...")
        res_lend = await client.post("/lending", headers=users["A"]["headers"], json={
            "book_id": book1_id,
            "borrower_email": users["B"]["email"],
        })
        assert res_lend.status_code == 201
        lending_id = res_lend.json()["id"]

        db = SessionLocal()
        try:
            lent_logs = db.query(ActivityLog).filter(
                ActivityLog.user_id == uuid.UUID(users["A"]["id"]),
                ActivityLog.action == "book_lent",
            ).all()
            assert len(lent_logs) == 1, f"Expected 1 book_lent log, got {len(lent_logs)}"
            assert lent_logs[0].details["borrower_email"] == users["B"]["email"]
            print("   [OK] Exactly 1 book_lent activity logged.")
        finally:
            db.close()

        # Test 17 & 18: Book return -> book_returned activity
        log_step(9, "Testing book return -> book_returned activity...")
        res_ret = await client.post(f"/lending/{lending_id}/return", headers=users["A"]["headers"])
        assert res_ret.status_code == 200

        db = SessionLocal()
        try:
            ret_logs = db.query(ActivityLog).filter(
                ActivityLog.user_id == uuid.UUID(users["A"]["id"]),
                ActivityLog.action == "book_returned",
            ).all()
            assert len(ret_logs) == 1, f"Expected 1 book_returned log, got {len(ret_logs)}"
            print("   [OK] Exactly 1 book_returned activity logged.")
        finally:
            db.close()

        # Test 19: Failed operations do NOT create activity records
        log_step(10, "Testing failed operation rollback (no activity recorded on failure)...")
        db = SessionLocal()
        count_before = db.query(ActivityLog).count()
        db.close()

        # Attempt invalid book creation (current_page > total_pages)
        res_fail = await client.post("/books", headers=users["A"]["headers"], json={
            "title": "Invalid Book",
            "author": "Nobody",
            "total_pages": 100,
            "current_page": 200,
        })
        assert res_fail.status_code == 422

        db = SessionLocal()
        count_after = db.query(ActivityLog).count()
        db.close()
        assert count_after == count_before, "Failed operation must not create activity log record!"
        print("   [OK] Failed operations create 0 activity records.")

        # Test 20: Activity feed ordering is newest-first
        log_step(11, "Testing activity feed ordering (newest first)...")
        res_feed = await client.get("/activities", headers=users["A"]["headers"])
        assert res_feed.status_code == 200
        feed_data = res_feed.json()
        items = feed_data["items"]
        assert len(items) >= 2, "Expected multiple activity items"
        for i in range(len(items) - 1):
            assert items[i]["created_at"] >= items[i + 1]["created_at"], "Activities must be ordered newest-first!"
        print(f"   [OK] Verified {len(items)} items correctly ordered newest-first.")

        # Test 21 & 22 & 23: Activity pagination
        log_step(12, "Testing activity pagination (page_size, total, total_pages)...")
        res_page1 = await client.get("/activities?page=1&page_size=3", headers=users["A"]["headers"])
        assert res_page1.status_code == 200
        p1 = res_page1.json()
        assert len(p1["items"]) == 3
        assert p1["page"] == 1
        assert p1["page_size"] == 3
        assert p1["total"] >= 6
        assert p1["total_pages"] >= 2

        res_page2 = await client.get("/activities?page=2&page_size=3", headers=users["A"]["headers"])
        assert res_page2.status_code == 200
        p2 = res_page2.json()
        assert len(p2["items"]) <= 3
        assert p2["page"] == 2
        # Ensure items on page 2 are distinct from page 1
        p1_ids = {item["id"] for item in p1["items"]}
        p2_ids = {item["id"] for item in p2["items"]}
        assert p1_ids.isdisjoint(p2_ids), "Page 1 and Page 2 items must not overlap!"
        print("   [OK] Activity pagination works with non-overlapping offsets.")

        # Test 24: Action filtering
        log_step(13, "Testing action filtering (?action=book_added)...")
        res_filter_action = await client.get("/activities?action=book_added", headers=users["A"]["headers"])
        assert res_filter_action.status_code == 200
        filtered_action = res_filter_action.json()
        assert filtered_action["total"] >= 1
        for item in filtered_action["items"]:
            assert item["action"] == "book_added"
        print(f"   [OK] Action filter verified ({filtered_action['total']} book_added events).")

        # Test 25: Shelf filtering
        log_step(14, "Testing shelf filtering (?shelf_id=...)...")
        res_filter_shelf = await client.get(f"/activities?shelf_id={shelf_id}", headers=users["A"]["headers"])
        assert res_filter_shelf.status_code == 200
        filtered_shelf = res_filter_shelf.json()
        assert filtered_shelf["total"] >= 1
        for item in filtered_shelf["items"]:
            assert item["shelf_id"] == shelf_id
        print(f"   [OK] Shelf filter verified ({filtered_shelf['total']} shelf events).")

        # Test 26, 27, 28: Shelf visibility scoping for collaborators and strangers
        log_step(15, "Testing shelf visibility scoping across collaborators and strangers...")
        # Re-share shelf with User C
        res_share_c = await client.post(f"/shelves/{shelf_id}/shares", headers=users["A"]["headers"], json={
            "email": users["C"]["email"],
            "role": "viewer",
        })
        assert res_share_c.status_code == 201
        share_c_id = res_share_c.json()["id"]

        # User C (active collaborator) CAN see activities for shelf_id
        res_c_feed = await client.get(f"/activities?shelf_id={shelf_id}", headers=users["C"]["headers"])
        assert res_c_feed.status_code == 200
        assert res_c_feed.json()["total"] >= 1
        print("   [OK] Active collaborator User C can access shared shelf activities.")

        # User D (uninvited stranger) CANNOT see activities for shelf_id (404 expected)
        res_d_shelf = await client.get(f"/activities?shelf_id={shelf_id}", headers=users["D"]["headers"])
        assert res_d_shelf.status_code == 404
        print("   [OK] Stranger User D receives 404 on inaccessible shelf filter.")

        # User D's general activity feed does NOT contain any items for shelf_id
        res_d_feed = await client.get("/activities", headers=users["D"]["headers"])
        assert res_d_feed.status_code == 200
        for item in res_d_feed.json()["items"]:
            assert item["shelf_id"] != shelf_id
        print("   [OK] Stranger User D general feed excludes private shelf activities.")

        # User C's share is removed -> User C loses access to shelf activities
        res_rm_c = await client.delete(f"/shelves/{shelf_id}/shares/{share_c_id}", headers=users["A"]["headers"])
        assert res_rm_c.status_code == 204

        res_c_after = await client.get(f"/activities?shelf_id={shelf_id}", headers=users["C"]["headers"])
        assert res_c_after.status_code == 404, f"Expected 404 after share removed, got {res_c_after.status_code}"

        res_c_gen = await client.get("/activities", headers=users["C"]["headers"])
        assert res_c_gen.status_code == 200
        for item in res_c_gen.json()["items"]:
            assert item["shelf_id"] != shelf_id, "User C must not see shelf activities after removal!"
        print("   [OK] Removed collaborator User C immediately loses access to shelf activities.")

        # Test 29: Personal book/progress activity is isolated to owner
        log_step(16, "Testing personal activity isolation...")
        res_d_gen2 = await client.get("/activities", headers=users["D"]["headers"])
        for item in res_d_gen2.json()["items"]:
            assert item["user_id"] == users["D"]["id"]
        print("   [OK] Personal book/progress activities strictly isolated.")

        # Test 30: Lending activity is visible to participants (lender and borrower)
        log_step(17, "Testing lending activity visibility for borrower User B...")
        res_b_feed = await client.get("/activities", headers=users["B"]["headers"])
        assert res_b_feed.status_code == 200
        b_actions = [it["action"] for it in res_b_feed.json()["items"]]
        assert "book_lent" in b_actions or "book_returned" in b_actions, "Borrower should see their lending activity!"
        # Stranger User D must NOT see User A's lending activity
        res_d_feed3 = await client.get("/activities", headers=users["D"]["headers"])
        d_actions = [it["action"] for it in res_d_feed3.json()["items"]]
        assert "book_lent" not in d_actions
        assert "book_returned" not in d_actions
        print("   [OK] Lending activity visible to borrower and isolated from strangers.")

        # Test 31: Empty activity feed metadata
        log_step(18, "Testing empty activity feed returns correct metadata...")
        # User D has performed no actions yet
        res_empty = await client.get("/activities", headers=users["D"]["headers"])
        assert res_empty.status_code == 200
        empty_data = res_empty.json()
        assert empty_data["items"] == []
        assert empty_data["total"] == 0
        assert empty_data["total_pages"] == 0
        assert empty_data["page"] == 1
        print("   [OK] Empty activity feed returns items=[], total=0, total_pages=0.")

    print("\nALL 21 TEST STEPS IN test_activity_phase8.py PASSED SUCCESSFULLY! [OK]")


if __name__ == "__main__":
    asyncio.run(run_tests())
