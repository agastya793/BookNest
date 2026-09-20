"""
Comprehensive Phase 7 Automated Test Suite for BookNest:
Peer-to-Peer Book Lending & Active Loan Enforcement

Verifies:
1. Registration of User A (lender), User B (borrower), and User C (third party).
2. User A creates Book A in their personal library.
3. User A successfully lends Book A to User B via POST /api/lending (201 Created).
4. Lending record has is_active = True and valid UTC lent_at timestamp.
5. Self-lending prevention: User A cannot lend book to themselves -> 400 Bad Request.
6. Nonexistent borrower prevention: lending to unregistered email -> 404 Not Found.
7. Borrower read-only access: User B accesses book via dedicated borrowed-book endpoint.
8. Strict book ownership isolation:
   - User B cannot PATCH borrowed book -> 404 Not Found.
   - User B cannot PUT borrowed book -> 404 Not Found.
   - User B cannot DELETE borrowed book -> 404 Not Found.
   - User B cannot update reading progress -> 404 Not Found.
   - User B cannot lend the borrowed book onward -> 404 Not Found.
9. Double-lending prevention: Attempting to lend actively lent book to User C -> 409 Conflict.
10. Non-owner lending prevention: User C cannot lend User A's book -> 404 Not Found.
11. Third-party isolation: User C cannot access private borrowed book details -> 404 Not Found.
12. Listing active loans:
    - User A lists active lent books (GET /api/lending?role=lender&status=active).
    - User B lists active borrowed books (GET /api/lending/borrowed and role=borrower).
    - User C sees no unrelated loans (empty list, and 404 on specific lending ID).
13. Return authorization:
    - Unauthorized User C cannot return the loan -> 403 Forbidden.
    - Owner/lender User A successfully returns the active loan -> 200 OK.
    - is_active becomes False and returned_at is populated.
14. Duplicate return prevention: Attempting to return already-returned loan -> 400 Bad Request.
15. Ownership preservation: Book A remains owned by User A and present in library.
16. Re-lending capability: Book A can be lent again to User C after being returned -> 201 Created.
17. Database-level concurrency invariant verification:
    - Direct SQLAlchemy test bypassing application logic verifies PostgreSQL partial
      unique index (ix_lending_active_book) raises IntegrityError on concurrent active loans.
18. Activity logging audit verification:
    - Exactly ONE ActivityLog entry created for 'book_lent'.
    - Exactly ONE ActivityLog entry created for 'book_returned'.
19. BookResponse metadata: is_lent and borrower_name accurately reflect active loan status.
20. Route precedence verification: GET /api/lending/book/{book_id} executes without route collision.
"""
import asyncio
import sys
import uuid
import httpx
from sqlalchemy.exc import IntegrityError
from app.database import SessionLocal
from app.models.activity_log import ActivityLog
from app.models.book import Book
from app.models.lending import Lending
from app.models.user import User

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://localhost:8000/api"


def log_step(num: int, title: str):
    print(f"\n[{num}/20] {title}")


async def run_tests():
    print("=== Starting Phase 7 Peer-to-Peer Book Lending & Active Loan Enforcement Test Suite ===\n")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        ts = int(asyncio.get_event_loop().time() * 1000)
        user_a_email = f"lender_a_{ts}@example.com"
        user_b_email = f"borrower_b_{ts}@example.com"
        user_c_email = f"thirdparty_c_{ts}@example.com"

        # Setup: Register User A, User B, and User C
        log_step(1, "Registering test users (Lender A, Borrower B, Third-party C)...")
        res_a = await client.post("/auth/signup", json={
            "name": "Alice Lender", "email": user_a_email, "password": "Pass@Word123"
        })
        assert res_a.status_code == 201, f"User A signup failed: {res_a.text}"
        token_a = res_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        res_b = await client.post("/auth/signup", json={
            "name": "Bob Borrower", "email": user_b_email, "password": "Pass@Word123"
        })
        assert res_b.status_code == 201, f"User B signup failed: {res_b.text}"
        token_b = res_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        res_c = await client.post("/auth/signup", json={
            "name": "Charlie Stranger", "email": user_c_email, "password": "Pass@Word123"
        })
        assert res_c.status_code == 201, f"User C signup failed: {res_c.text}"
        token_c = res_c.json()["access_token"]
        headers_c = {"Authorization": f"Bearer {token_c}"}
        print("   [OK] Registered User A, User B, and User C.")

        # Setup: User A creates Book A
        log_step(2, "User A creates Book A in their personal library...")
        res_book = await client.post("/books", headers=headers_a, json={
            "title": "Clean Architecture",
            "author": "Robert C. Martin",
            "status": "want_to_read",
            "total_pages": 432,
            "current_page": 0,
        })
        assert res_book.status_code == 201, f"Book creation failed: {res_book.text}"
        book_a = res_book.json()
        book_a_id = book_a["id"]
        assert book_a["is_lent"] is False
        print(f"   [OK] Book created: '{book_a['title']}' (ID: {book_a_id})")

        # Test 3: User A lends Book A to User B
        log_step(3, "User A lends Book A to User B via POST /api/lending...")
        res_lend = await client.post("/lending", headers=headers_a, json={
            "book_id": book_a_id,
            "borrower_email": user_b_email,
        })
        assert res_lend.status_code == 201, f"Lend failed: {res_lend.text}"
        lending_data = res_lend.json()
        lending_id = lending_data["id"]
        assert lending_data["book_id"] == book_a_id
        assert lending_data["borrower_email"] == user_b_email
        assert lending_data["is_active"] is True
        assert lending_data["returned_at"] is None
        assert lending_data["lent_at"] is not None
        print(f"   [OK] Book lent successfully (Lending ID: {lending_id}).")

        # Test 4: Book metadata reflects active loan
        log_step(4, "Verifying BookResponse reflects active lending metadata...")
        res_book_check = await client.get(f"/books/{book_a_id}", headers=headers_a)
        assert res_book_check.status_code == 200
        book_info = res_book_check.json()
        assert book_info["is_lent"] is True
        assert book_info["active_lending_id"] == lending_id
        assert book_info["borrower_name"] == "Bob Borrower"
        print("   [OK] BookResponse accurately reports is_lent=True and borrower_name.")

        # Test 5: Self-lending is rejected with 400 Bad Request
        log_step(5, "Testing self-lending rejection (User A lending to User A)...")
        res_self = await client.post("/lending", headers=headers_a, json={
            "book_id": book_a_id,
            "borrower_email": user_a_email,
        })
        assert res_self.status_code == 400, f"Expected 400, got {res_self.status_code}: {res_self.text}"
        assert "yourself" in res_self.json()["detail"].lower()
        print("   [OK] Self-lending cleanly rejected with 400 Bad Request.")

        # Test 6: Lending to nonexistent email is rejected with 404 Not Found
        log_step(6, "Testing lending to nonexistent email rejection...")
        res_nonexistent = await client.post("/lending", headers=headers_a, json={
            "book_id": book_a_id,
            "borrower_email": "nonexistent_ghost_reader@example.com",
        })
        assert res_nonexistent.status_code == 404, f"Expected 404, got {res_nonexistent.status_code}"
        print("   [OK] Lending to unregistered email rejected with 404 Not Found.")

        # Test 7: Double-lending prevention (409 Conflict)
        log_step(7, "Testing double-lending prevention while active loan exists...")
        res_double = await client.post("/lending", headers=headers_a, json={
            "book_id": book_a_id,
            "borrower_email": user_c_email,
        })
        assert res_double.status_code == 409, f"Expected 409 Conflict, got {res_double.status_code}: {res_double.text}"
        assert "already actively lent" in res_double.json()["detail"].lower()
        print("   [OK] Double-lending rejected with 409 Conflict.")

        # Test 8: Borrower gets read-only access via dedicated borrowed-book flow
        log_step(8, "Testing borrower read-only access via GET /api/lending/borrowed...")
        res_borrowed_list = await client.get("/lending/borrowed", headers=headers_b)
        assert res_borrowed_list.status_code == 200
        borrowed_items = res_borrowed_list.json()
        assert len(borrowed_items) == 1
        assert borrowed_items[0]["book_id"] == book_a_id
        assert borrowed_items[0]["title"] == "Clean Architecture"
        assert borrowed_items[0]["lender_name"] == "Alice Lender"

        res_borrowed_detail = await client.get(f"/lending/borrowed/{book_a_id}", headers=headers_b)
        assert res_borrowed_detail.status_code == 200
        assert res_borrowed_detail.json()["book_id"] == book_a_id
        print("   [OK] Borrower accesses read-only book representation successfully.")

        # Test 9: Borrower CANNOT use owner CRUD endpoints on borrowed book
        log_step(9, "Verifying Borrower CANNOT execute owner mutations on borrowed book...")
        res_patch = await client.patch(f"/books/{book_a_id}", headers=headers_b, json={"title": "Hacked Title"})
        assert res_patch.status_code == 404, f"Expected 404 on borrower PATCH, got {res_patch.status_code}"

        res_put = await client.put(f"/books/{book_a_id}", headers=headers_b, json={"title": "Hacked Title"})
        assert res_put.status_code == 404, f"Expected 404 on borrower PUT, got {res_put.status_code}"

        res_del = await client.delete(f"/books/{book_a_id}", headers=headers_b)
        assert res_del.status_code == 404, f"Expected 404 on borrower DELETE, got {res_del.status_code}"

        res_prog = await client.post(f"/books/{book_a_id}/progress", headers=headers_b, json={"current_page": 50})
        assert res_prog.status_code == 404, f"Expected 404 on borrower progress update, got {res_prog.status_code}"

        res_sublend = await client.post("/lending", headers=headers_b, json={
            "book_id": book_a_id, "borrower_email": user_c_email
        })
        assert res_sublend.status_code == 404, f"Expected 404 on borrower sub-lending, got {res_sublend.status_code}"
        print("   [OK] Borrower strictly barred from owner mutations (all returned 404 Not Found).")

        # Test 10: Non-owner User C cannot lend User A's book
        log_step(10, "Verifying third-party User C cannot lend User A's book...")
        res_c_lend = await client.post("/lending", headers=headers_c, json={
            "book_id": book_a_id, "borrower_email": user_b_email
        })
        assert res_c_lend.status_code == 404
        print("   [OK] Unauthorized lending attempt rejected with 404 Not Found.")

        # Test 11: Third-party User C cannot access borrowed book details
        log_step(11, "Verifying third-party User C cannot access borrowed book details...")
        res_c_borrowed = await client.get(f"/lending/borrowed/{book_a_id}", headers=headers_c)
        assert res_c_borrowed.status_code == 404
        print("   [OK] Unrelated third-party denied access with 404 Not Found.")

        # Test 12: Listing active loans as lender and borrower
        log_step(12, "Verifying lending list endpoints with role and status filters...")
        res_lent_list = await client.get("/lending?role=lender&status=active", headers=headers_a)
        assert res_lent_list.status_code == 200
        assert len(res_lent_list.json()) == 1
        assert res_lent_list.json()[0]["id"] == lending_id

        res_borrowed_q = await client.get("/lending?role=borrower&status=active", headers=headers_b)
        assert res_borrowed_q.status_code == 200
        assert len(res_borrowed_q.json()) == 1
        assert res_borrowed_q.json()[0]["id"] == lending_id

        res_c_list = await client.get("/lending", headers=headers_c)
        assert res_c_list.status_code == 200
        assert len(res_c_list.json()) == 0

        res_c_detail = await client.get(f"/lending/{lending_id}", headers=headers_c)
        assert res_c_detail.status_code == 404
        print("   [OK] Filtered loan listings and lending detail isolation verified.")

        # Test 13: Unauthorized return attempt by User C is rejected
        log_step(13, "Verifying third-party User C cannot return the loan...")
        res_c_return = await client.post(f"/lending/{lending_id}/return", headers=headers_c)
        assert res_c_return.status_code == 403, f"Expected 403, got {res_c_return.status_code}"
        print("   [OK] Unauthorized return rejected with 403 Forbidden.")

        # Test 14: Owner/lender User A returns the book
        log_step(14, "Owner User A marks the active loan as returned...")
        res_return = await client.post(f"/lending/{lending_id}/return", headers=headers_a)
        assert res_return.status_code == 200, f"Return failed: {res_return.text}"
        returned_data = res_return.json()
        assert returned_data["is_active"] is False
        assert returned_data["returned_at"] is not None
        print("   [OK] Loan returned successfully; is_active=False and returned_at recorded.")

        # Test 15: Duplicate return attempt is rejected with 400 Bad Request
        log_step(15, "Verifying duplicate return attempt is rejected...")
        res_dup_return = await client.post(f"/lending/{lending_id}/return", headers=headers_a)
        assert res_dup_return.status_code == 400, f"Expected 400, got {res_dup_return.status_code}"
        assert "already been returned" in res_dup_return.json()["detail"].lower()
        print("   [OK] Duplicate return rejected with 400 Bad Request.")

        # Test 16: Book remains in User A's catalog with is_lent = False
        log_step(16, "Verifying book ownership and availability after return...")
        res_book_after = await client.get(f"/books/{book_a_id}", headers=headers_a)
        assert res_book_after.status_code == 200
        book_after = res_book_after.json()
        assert book_after["is_lent"] is False
        assert book_after["active_lending_id"] is None
        print("   [OK] Book remains owned by User A and is available again.")

        # Test 17: Re-lending capability
        log_step(17, "Testing re-lending: User A lends Book A to User C after previous return...")
        res_relend = await client.post("/lending", headers=headers_a, json={
            "book_id": book_a_id, "borrower_email": user_c_email
        })
        assert res_relend.status_code == 201
        new_lending_id = res_relend.json()["id"]
        assert new_lending_id != lending_id
        assert res_relend.json()["borrower_email"] == user_c_email
        print("   [OK] Book re-lent successfully to User C.")

        # Return second loan for clean state
        res_ret2 = await client.post(f"/lending/{new_lending_id}/return", headers=headers_a)
        assert res_ret2.status_code == 200

        # Test 18: Lending history endpoint and route ordering
        log_step(18, "Verifying owner lending history route GET /api/lending/book/{book_id}...")
        res_history = await client.get(f"/lending/book/{book_a_id}", headers=headers_a)
        assert res_history.status_code == 200
        history_records = res_history.json()
        assert len(history_records) == 2  # Lent to B, then to C
        print(f"   [OK] Successfully retrieved {len(history_records)} loan history records.")

        # Test 19: ActivityLog verification
        log_step(19, "Verifying ActivityLog entries for book_lent and book_returned...")
        db = SessionLocal()
        try:
            lent_logs = (
                db.query(ActivityLog)
                .filter(ActivityLog.user_id == uuid.UUID(book_a["user_id"]), ActivityLog.action == "book_lent")
                .all()
            )
            returned_logs = (
                db.query(ActivityLog)
                .filter(ActivityLog.user_id == uuid.UUID(book_a["user_id"]), ActivityLog.action == "book_returned")
                .all()
            )
            assert len(lent_logs) == 2, f"Expected 2 book_lent logs, got {len(lent_logs)}"
            assert len(returned_logs) == 2, f"Expected 2 book_returned logs, got {len(returned_logs)}"
            for l in lent_logs:
                assert "book_id" in l.details
                assert "borrower_email" in l.details
            print(f"   [OK] ActivityLog verified: 2 'book_lent' and 2 'book_returned' entries.")
        finally:
            db.close()

        # Test 20: Database constraint concurrency enforcement (ix_lending_active_book)
        log_step(20, "Verifying PostgreSQL partial unique index (ix_lending_active_book) blocks race condition...")
        db1 = SessionLocal()
        db2 = SessionLocal()
        try:
            user_a_db = db1.query(User).filter(User.email == user_a_email).first()
            user_b_db = db1.query(User).filter(User.email == user_b_email).first()
            user_c_db = db1.query(User).filter(User.email == user_c_email).first()

            # Insert first active lending in db1
            loan1 = Lending(
                book_id=uuid.UUID(book_a_id),
                lender_id=user_a_db.id,
                borrower_id=user_b_db.id,
                is_active=True,
            )
            db1.add(loan1)
            db1.commit()

            # Attempt to insert second active lending in db2 bypassing app checks
            loan2 = Lending(
                book_id=uuid.UUID(book_a_id),
                lender_id=user_a_db.id,
                borrower_id=user_c_db.id,
                is_active=True,
            )
            db2.add(loan2)
            raised_integrity_error = False
            try:
                db2.commit()
            except IntegrityError as e:
                raised_integrity_error = True
                db2.rollback()

            assert raised_integrity_error is True, "PostgreSQL partial unique index failed to raise IntegrityError!"
            print("   [OK] PostgreSQL partial unique index (ix_lending_active_book) successfully enforced!")

            # Clean up test loan1
            db1.delete(loan1)
            db1.commit()
        finally:
            db1.close()
            db2.close()

    print("\nALL 20 PHASE 7 AUTOMATED VERIFICATION CHECKS PASSED SUCCESSFULLY! [OK]")


if __name__ == "__main__":
    asyncio.run(run_tests())
