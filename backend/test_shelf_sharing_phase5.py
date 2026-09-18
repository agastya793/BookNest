"""
Comprehensive Phase 5 Automated Test Suite for BookNest:
Shared Shelves & Role-Based Access Control (RBAC)

Verifies:
1. Owner creates a shelf.
2. Owner shares with User B as viewer.
3. Owner shares with User C as editor.
4. Nonexistent invitee email returns 404.
5. Owner cannot invite themselves -> 400.
6. Duplicate share returns 409.
7. Viewer can read shelf details.
8. Viewer can read shelf books.
9. Viewer cannot add a book -> 403.
10. Viewer cannot remove a book -> 403.
11. Editor can read shelf details.
12. Editor can add THEIR OWN book to the shared shelf.
13. Editor can remove a book from the shared shelf.
14. Editor cannot rename shelf -> 403.
15. Editor cannot delete shelf -> 403.
16. Editor cannot invite collaborators -> 403.
17. Editor cannot change roles -> 403.
18. Viewer cannot rename/delete/manage collaborators -> 403.
19. Uninvited User D receives 404 when accessing the shelf.
20. Owner can change viewer -> editor.
21. Owner can change editor -> viewer.
22. Collaborator can leave by deleting THEIR OWN share.
23. Collaborator cannot delete another collaborator's share -> 403.
24. Removed collaborator immediately loses shelf access.
25. Shared shelf can contain books owned by multiple users.
26. Each owner still retains ownership of their own books.
27. Deleting the shelf removes shelf_shares.
28. Deleting the shelf removes shelf_books.
29. Deleting the shelf preserves every actual Book record.
"""
import sys
import uuid
import httpx
from app.database import SessionLocal
from app.models import Shelf, ShelfBook, ShelfShare, Book

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"


def log_step(step_num: int, title: str):
    print(f"\n[{step_num}/29] {title}")


def assert_status(resp: httpx.Response, expected: int, action: str):
    if resp.status_code != expected:
        print(f"FAILED: {action} - Expected {expected}, got {resp.status_code}")
        print(f"Detail: {resp.text}")
        sys.exit(1)
    print(f"  OK: {action} ({resp.status_code})")


def run_tests():
    client = httpx.Client(base_url=BASE_URL, timeout=15.0)

    # -------------------------------------------------------------
    # Setup Test Users
    # User A (Owner), User B (Viewer/Editor), User C (Editor), User D (Uninvited)
    # -------------------------------------------------------------
    print("=== Phase 5: Setting up Test Users ===")
    uid = uuid.uuid4().hex[:6]
    users = {}
    for letter, name in [("A", "Alice Owner"), ("B", "Bob Collaborator"), ("C", "Carol Editor"), ("D", "Dave Stranger")]:
        email = f"user_{letter.lower()}_{uid}@example.com"
        pwd = "Password123!"
        resp = client.post("/api/auth/signup", json={"email": email, "password": pwd, "name": name})
        assert_status(resp, 201, f"Signup User {letter} ({email})")
        data = resp.json()
        users[letter] = {
            "email": email,
            "id": data["user"]["id"],
            "name": name,
            "headers": {"Authorization": f"Bearer {data['access_token']}"},
        }

    # -------------------------------------------------------------
    # 1. Owner creates a shelf
    # -------------------------------------------------------------
    log_step(1, "Owner creates a shelf")
    resp = client.post("/api/shelves", headers=users["A"]["headers"], json={"name": f"Sci-Fi Collab {uid}"})
    assert_status(resp, 201, "User A creates custom shelf")
    shelf = resp.json()
    shelf_id = shelf["id"]
    assert shelf["role"] == "owner", f"Expected role 'owner', got {shelf['role']}"

    # Owner creates a book and adds it to shelf
    resp = client.post(
        "/api/books",
        headers=users["A"]["headers"],
        json={"title": "Dune", "author": "Frank Herbert", "total_pages": 600}
    )
    assert_status(resp, 201, "User A creates book 'Dune'")
    book_a_id = resp.json()["id"]

    resp = client.post(f"/api/shelves/{shelf_id}/books", headers=users["A"]["headers"], json={"book_id": book_a_id})
    assert_status(resp, 201, "User A adds 'Dune' to shelf")

    # -------------------------------------------------------------
    # 2. Owner shares with User B as viewer
    # -------------------------------------------------------------
    log_step(2, "Owner shares with User B as viewer")
    resp = client.post(
        f"/api/shelves/{shelf_id}/shares",
        headers=users["A"]["headers"],
        json={"email": users["B"]["email"], "role": "viewer"}
    )
    assert_status(resp, 201, "User A shares shelf with User B as viewer")
    share_b = resp.json()
    share_b_id = share_b["id"]
    assert share_b["role"] == "viewer"
    assert share_b["user_email"] == users["B"]["email"]

    # -------------------------------------------------------------
    # 3. Owner shares with User C as editor
    # -------------------------------------------------------------
    log_step(3, "Owner shares with User C as editor")
    resp = client.post(
        f"/api/shelves/{shelf_id}/shares",
        headers=users["A"]["headers"],
        json={"email": users["C"]["email"], "role": "editor"}
    )
    assert_status(resp, 201, "User A shares shelf with User C as editor")
    share_c = resp.json()
    share_c_id = share_c["id"]
    assert share_c["role"] == "editor"
    assert share_c["user_email"] == users["C"]["email"]

    # -------------------------------------------------------------
    # 4. Nonexistent invitee email returns 404
    # -------------------------------------------------------------
    log_step(4, "Nonexistent invitee email returns 404")
    resp = client.post(
        f"/api/shelves/{shelf_id}/shares",
        headers=users["A"]["headers"],
        json={"email": "nonexistent_ghost_user_xyz@example.com", "role": "viewer"}
    )
    assert_status(resp, 404, "Inviting nonexistent email rejected with 404")

    # -------------------------------------------------------------
    # 5. Owner cannot invite themselves -> 400
    # -------------------------------------------------------------
    log_step(5, "Owner cannot invite themselves -> 400")
    resp = client.post(
        f"/api/shelves/{shelf_id}/shares",
        headers=users["A"]["headers"],
        json={"email": users["A"]["email"], "role": "editor"}
    )
    assert_status(resp, 400, "Owner self-invite rejected with 400")

    # -------------------------------------------------------------
    # 6. Duplicate share returns 409
    # -------------------------------------------------------------
    log_step(6, "Duplicate share returns 409")
    resp = client.post(
        f"/api/shelves/{shelf_id}/shares",
        headers=users["A"]["headers"],
        json={"email": users["B"]["email"], "role": "editor"}
    )
    assert_status(resp, 409, "Duplicate share with User B rejected with 409")

    # -------------------------------------------------------------
    # 7. Viewer can read shelf details
    # -------------------------------------------------------------
    log_step(7, "Viewer can read shelf details")
    resp = client.get(f"/api/shelves/{shelf_id}", headers=users["B"]["headers"])
    assert_status(resp, 200, "User B (viewer) reads shelf detail")
    data_b = resp.json()
    assert data_b["role"] == "viewer", f"Expected role viewer, got {data_b['role']}"
    assert len(data_b["books"]) == 1
    assert data_b["books"][0]["id"] == book_a_id

    # Check listing endpoint GET /api/shelves for User B
    resp = client.get("/api/shelves", headers=users["B"]["headers"])
    assert_status(resp, 200, "User B lists shelves")
    b_shelves = resp.json()
    b_shared = [s for s in b_shelves if s["id"] == shelf_id]
    assert len(b_shared) == 1, "Shelf should appear in User B's shelves list"
    assert b_shared[0]["role"] == "viewer"
    assert b_shared[0]["is_shared"] is True
    assert b_shared[0]["owner_name"] == users["A"]["name"]

    # -------------------------------------------------------------
    # 8. Viewer can read shelf books via GET /api/books?shelf_id=...
    # -------------------------------------------------------------
    log_step(8, "Viewer can read shelf books")
    resp = client.get(f"/api/books?shelf_id={shelf_id}", headers=users["B"]["headers"])
    assert_status(resp, 200, "User B (viewer) filters catalog by shelf_id")
    books_data = resp.json()
    assert books_data["total"] == 1
    assert books_data["items"][0]["id"] == book_a_id

    # -------------------------------------------------------------
    # 9. Viewer cannot add a book -> 403
    # -------------------------------------------------------------
    log_step(9, "Viewer cannot add a book -> 403")
    # First User B creates a book in their library
    resp = client.post(
        "/api/books",
        headers=users["B"]["headers"],
        json={"title": "Bob's Book", "author": "Bob Author"}
    )
    assert_status(resp, 201, "User B creates own book")
    book_b_id = resp.json()["id"]

    resp = client.post(
        f"/api/shelves/{shelf_id}/books",
        headers=users["B"]["headers"],
        json={"book_id": book_b_id}
    )
    assert_status(resp, 403, "Viewer adding book rejected with 403")

    # -------------------------------------------------------------
    # 10. Viewer cannot remove a book -> 403
    # -------------------------------------------------------------
    log_step(10, "Viewer cannot remove a book -> 403")
    resp = client.delete(f"/api/shelves/{shelf_id}/books/{book_a_id}", headers=users["B"]["headers"])
    assert_status(resp, 403, "Viewer removing book rejected with 403")

    # -------------------------------------------------------------
    # 11. Editor can read shelf details
    # -------------------------------------------------------------
    log_step(11, "Editor can read shelf details")
    resp = client.get(f"/api/shelves/{shelf_id}", headers=users["C"]["headers"])
    assert_status(resp, 200, "User C (editor) reads shelf detail")
    data_c = resp.json()
    assert data_c["role"] == "editor"

    # -------------------------------------------------------------
    # 12. Editor can add THEIR OWN book to the shared shelf
    # -------------------------------------------------------------
    log_step(12, "Editor can add THEIR OWN book to the shared shelf")
    resp = client.post(
        "/api/books",
        headers=users["C"]["headers"],
        json={"title": "Carol's SciFi", "author": "Carol Author", "total_pages": 420}
    )
    assert_status(resp, 201, "User C creates own book")
    book_c_id = resp.json()["id"]

    resp = client.post(
        f"/api/shelves/{shelf_id}/books",
        headers=users["C"]["headers"],
        json={"book_id": book_c_id}
    )
    assert_status(resp, 201, "User C (editor) adds own book to shared shelf")

    # Verify book is now visible on the shelf
    resp = client.get(f"/api/shelves/{shelf_id}", headers=users["A"]["headers"])
    assert resp.json()["book_count"] == 2

    # Verify editor CANNOT add another user's book (e.g. User B's book)
    resp = client.post(
        f"/api/shelves/{shelf_id}/books",
        headers=users["C"]["headers"],
        json={"book_id": book_b_id}
    )
    assert_status(resp, 404, "Editor cannot add another user's book (returns 404)")

    # -------------------------------------------------------------
    # 13. Editor can remove a book from the shared shelf
    # -------------------------------------------------------------
    log_step(13, "Editor can remove a book from the shared shelf")
    # Editor removes book_c_id from the shelf
    resp = client.delete(f"/api/shelves/{shelf_id}/books/{book_c_id}", headers=users["C"]["headers"])
    assert_status(resp, 204, "Editor removes book from shared shelf")

    # Re-add it so shelf has both books for multi-user tests later
    resp = client.post(
        f"/api/shelves/{shelf_id}/books",
        headers=users["C"]["headers"],
        json={"book_id": book_c_id}
    )
    assert_status(resp, 201, "Re-add book_c to shelf")

    # -------------------------------------------------------------
    # 14. Editor cannot rename shelf -> 403
    # -------------------------------------------------------------
    log_step(14, "Editor cannot rename shelf -> 403")
    resp = client.patch(f"/api/shelves/{shelf_id}", headers=users["C"]["headers"], json={"name": "Hacked Name"})
    assert_status(resp, 403, "Editor rename rejected with 403")

    # -------------------------------------------------------------
    # 15. Editor cannot delete shelf -> 403
    # -------------------------------------------------------------
    log_step(15, "Editor cannot delete shelf -> 403")
    resp = client.delete(f"/api/shelves/{shelf_id}", headers=users["C"]["headers"])
    assert_status(resp, 403, "Editor delete rejected with 403")

    # -------------------------------------------------------------
    # 16. Editor cannot invite collaborators -> 403
    # -------------------------------------------------------------
    log_step(16, "Editor cannot invite collaborators -> 403")
    resp = client.post(
        f"/api/shelves/{shelf_id}/shares",
        headers=users["C"]["headers"],
        json={"email": users["D"]["email"], "role": "viewer"}
    )
    assert_status(resp, 403, "Editor invite rejected with 403")

    # -------------------------------------------------------------
    # 17. Editor cannot change roles -> 403
    # -------------------------------------------------------------
    log_step(17, "Editor cannot change roles -> 403")
    resp = client.patch(
        f"/api/shelves/{shelf_id}/shares/{share_b_id}",
        headers=users["C"]["headers"],
        json={"role": "editor"}
    )
    assert_status(resp, 403, "Editor change role rejected with 403")

    # -------------------------------------------------------------
    # 18. Viewer cannot rename/delete/manage collaborators
    # -------------------------------------------------------------
    log_step(18, "Viewer cannot rename/delete/manage collaborators")
    resp = client.patch(f"/api/shelves/{shelf_id}", headers=users["B"]["headers"], json={"name": "Viewer Rename"})
    assert_status(resp, 403, "Viewer rename rejected with 403")

    resp = client.delete(f"/api/shelves/{shelf_id}", headers=users["B"]["headers"])
    assert_status(resp, 403, "Viewer delete rejected with 403")

    resp = client.post(
        f"/api/shelves/{shelf_id}/shares",
        headers=users["B"]["headers"],
        json={"email": users["D"]["email"], "role": "viewer"}
    )
    assert_status(resp, 403, "Viewer invite rejected with 403")

    resp = client.patch(
        f"/api/shelves/{shelf_id}/shares/{share_c_id}",
        headers=users["B"]["headers"],
        json={"role": "viewer"}
    )
    assert_status(resp, 403, "Viewer change role rejected with 403")

    # -------------------------------------------------------------
    # 19. Uninvited User D receives 404 when accessing the shelf
    # -------------------------------------------------------------
    log_step(19, "Uninvited User D receives 404 when accessing the shelf")
    resp = client.get(f"/api/shelves/{shelf_id}", headers=users["D"]["headers"])
    assert_status(resp, 404, "User D GET shelf rejected with 404 (no existence leak)")

    resp = client.get(f"/api/books?shelf_id={shelf_id}", headers=users["D"]["headers"])
    assert_status(resp, 404, "User D GET books?shelf_id=... rejected with 404")

    resp = client.post(
        f"/api/shelves/{shelf_id}/books",
        headers=users["D"]["headers"],
        json={"book_id": book_a_id}
    )
    assert_status(resp, 404, "User D add book rejected with 404")

    # -------------------------------------------------------------
    # 20. Owner can change viewer -> editor
    # -------------------------------------------------------------
    log_step(20, "Owner can change viewer -> editor")
    resp = client.patch(
        f"/api/shelves/{shelf_id}/shares/{share_b_id}",
        headers=users["A"]["headers"],
        json={"role": "editor"}
    )
    assert_status(resp, 200, "Owner promotes User B to editor")
    assert resp.json()["role"] == "editor"

    # User B now has editor rights: can add book_b
    resp = client.post(
        f"/api/shelves/{shelf_id}/books",
        headers=users["B"]["headers"],
        json={"book_id": book_b_id}
    )
    assert_status(resp, 201, "User B (now editor) successfully adds own book")

    # -------------------------------------------------------------
    # 21. Owner can change editor -> viewer
    # -------------------------------------------------------------
    log_step(21, "Owner can change editor -> viewer")
    resp = client.patch(
        f"/api/shelves/{shelf_id}/shares/{share_b_id}",
        headers=users["A"]["headers"],
        json={"role": "viewer"}
    )
    assert_status(resp, 200, "Owner demotes User B back to viewer")
    assert resp.json()["role"] == "viewer"

    # User B now cannot add another book
    resp = client.post(
        f"/api/shelves/{shelf_id}/books",
        headers=users["B"]["headers"],
        json={"book_id": book_b_id}
    )
    assert_status(resp, 403, "User B (demoted to viewer) blocked from adding book with 403")

    # -------------------------------------------------------------
    # 22. Collaborator can leave by deleting THEIR OWN share
    # -------------------------------------------------------------
    log_step(22, "Collaborator can leave by deleting THEIR OWN share")
    # User B leaves shelf by deleting share_b_id
    resp = client.delete(f"/api/shelves/{shelf_id}/shares/{share_b_id}", headers=users["B"]["headers"])
    assert_status(resp, 204, "User B successfully leaves shelf")

    # -------------------------------------------------------------
    # 23. Collaborator cannot delete another collaborator's share
    # -------------------------------------------------------------
    log_step(23, "Collaborator cannot delete another collaborator's share")
    # Invite User B back as viewer to test deletion of User C's share
    resp = client.post(
        f"/api/shelves/{shelf_id}/shares",
        headers=users["A"]["headers"],
        json={"email": users["B"]["email"], "role": "viewer"}
    )
    assert_status(resp, 201, "Re-invite User B")
    new_share_b_id = resp.json()["id"]

    # User B attempts to delete User C's share
    resp = client.delete(f"/api/shelves/{shelf_id}/shares/{share_c_id}", headers=users["B"]["headers"])
    assert_status(resp, 403, "User B deleting User C share rejected with 403")

    # -------------------------------------------------------------
    # 24. Removed collaborator immediately loses shelf access
    # -------------------------------------------------------------
    log_step(24, "Removed collaborator immediately loses shelf access")
    # Owner removes User B
    resp = client.delete(f"/api/shelves/{shelf_id}/shares/{new_share_b_id}", headers=users["A"]["headers"])
    assert_status(resp, 204, "Owner removes User B")

    # User B immediately receives 404
    resp = client.get(f"/api/shelves/{shelf_id}", headers=users["B"]["headers"])
    assert_status(resp, 404, "User B receives 404 on shelf access")

    resp = client.get(f"/api/books?shelf_id={shelf_id}", headers=users["B"]["headers"])
    assert_status(resp, 404, "User B receives 404 on books filter")

    # -------------------------------------------------------------
    # 25. Shared shelf can contain books owned by multiple users
    # -------------------------------------------------------------
    log_step(25, "Shared shelf can contain books owned by multiple users")
    resp = client.get(f"/api/shelves/{shelf_id}", headers=users["A"]["headers"])
    assert_status(resp, 200, "Owner reads shelf")
    shelf_detail = resp.json()
    book_ids_on_shelf = [b["id"] for b in shelf_detail["books"]]
    assert book_a_id in book_ids_on_shelf, "User A's book should be on shelf"
    assert book_c_id in book_ids_on_shelf, "User C's book should be on shelf"
    print(f"  OK: Shelf contains books from multiple owners (User A: {book_a_id}, User C: {book_c_id})")

    # -------------------------------------------------------------
    # 26. Each owner still retains ownership of their own books
    # -------------------------------------------------------------
    log_step(26, "Each owner still retains ownership of their own books")
    # User C cannot edit or delete User A's book
    resp = client.patch(f"/api/books/{book_a_id}", headers=users["C"]["headers"], json={"title": "Hacked Dune"})
    assert_status(resp, 404, "User C cannot edit User A book (404 Not Found in personal library)")

    resp = client.delete(f"/api/books/{book_a_id}", headers=users["C"]["headers"])
    assert_status(resp, 404, "User C cannot delete User A book (404 Not Found in personal library)")

    # User C CAN edit their own book
    resp = client.patch(f"/api/books/{book_c_id}", headers=users["C"]["headers"], json={"notes": "Great read!"})
    assert_status(resp, 200, "User C can edit own book")
    assert resp.json()["notes"] == "Great read!"

    # -------------------------------------------------------------
    # 27, 28, 29. Deleting shelf removes shares, books join rows, and preserves books
    # -------------------------------------------------------------
    log_step(27, "Deleting shelf removes shelf_shares")
    log_step(28, "Deleting shelf removes shelf_books")
    log_step(29, "Deleting shelf preserves every actual Book record")

    # Delete shelf as User A (owner)
    resp = client.delete(f"/api/shelves/{shelf_id}", headers=users["A"]["headers"])
    assert_status(resp, 204, "Owner deletes custom shelf")

    # Verify shelf is gone
    resp = client.get(f"/api/shelves/{shelf_id}", headers=users["A"]["headers"])
    assert_status(resp, 404, "Shelf no longer exists")

    # Direct database verification of join table cascade cleanup
    db = SessionLocal()
    try:
        shares_remaining = db.query(ShelfShare).filter(ShelfShare.shelf_id == shelf_id).count()
        assert shares_remaining == 0, f"Expected 0 shelf_shares, found {shares_remaining}"
        print("  OK: All shelf_shares cascade deleted from database")

        shelf_books_remaining = db.query(ShelfBook).filter(ShelfBook.shelf_id == shelf_id).count()
        assert shelf_books_remaining == 0, f"Expected 0 shelf_books, found {shelf_books_remaining}"
        print("  OK: All shelf_books cascade deleted from database")

        # Verify books STILL EXIST in database
        book_a = db.query(Book).filter(Book.id == book_a_id).first()
        assert book_a is not None, "Book A must still exist in DB!"
        assert str(book_a.user_id) == users["A"]["id"]

        book_c = db.query(Book).filter(Book.id == book_c_id).first()
        assert book_c is not None, "Book C must still exist in DB!"
        assert str(book_c.user_id) == users["C"]["id"]
        print("  OK: All actual Book records preserved in DB!")
    finally:
        db.close()

    # API verification that books still exist in their owners' catalogs
    resp = client.get(f"/api/books/{book_a_id}", headers=users["A"]["headers"])
    assert_status(resp, 200, "User A still has Book A in personal library")

    resp = client.get(f"/api/books/{book_c_id}", headers=users["C"]["headers"])
    assert_status(resp, 200, "User C still has Book C in personal library")

    print("\n=======================================================")
    print("ALL 29 PHASE 5 RBAC & SHARING FUNCTIONAL TESTS PASSED!")
    print("=======================================================")


if __name__ == "__main__":
    run_tests()
