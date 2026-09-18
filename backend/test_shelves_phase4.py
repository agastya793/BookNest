"""
Comprehensive Phase 4 Automated Test Suite for BookNest:
- Shelf CRUD (create, list with book_count, get detail with books, update/rename, delete)
- Engine constraint verification (409 Conflict for duplicate shelf name per user via uq_shelf_user_name)
- Many-to-many relationship (single book on multiple shelves, shelf with multiple books)
- Duplicate book on shelf prevention (409 Conflict via uq_shelf_book)
- Cascade safety (deleting shelf removes join rows but leaves books intact; removing book from shelf leaves book intact)
- Multi-user isolation (User B cannot view/edit/delete User A shelves or attach User A books)
- Shelf filtering (GET /api/books?shelf_id=...)
"""
import sys
import uuid
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"


def log_step(name: str):
    print(f"\n=== {name} ===")


def assert_status(response: httpx.Response, expected: int, msg: str):
    if response.status_code != expected:
        print(f"[FAIL] {msg}: expected {expected}, got {response.status_code}")
        print(f"Response body: {response.text}")
        sys.exit(1)
    print(f"[OK] {msg} ({response.status_code})")


def run_tests():
    client = httpx.Client(base_url=BASE_URL, timeout=10.0)

    # 1. Setup User A
    log_step("1. Setup User A")
    user_a_email = f"user_a_{uuid.uuid4().hex[:8]}@example.com"
    user_a_password = "SecurePassword123!"

    resp = client.post("/api/auth/signup", json={"email": user_a_email, "password": user_a_password})
    assert_status(resp, 201, "User A signup")
    token_a = resp.json()["access_token"]
    auth_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Setup User B
    log_step("2. Setup User B")
    user_b_email = f"user_b_{uuid.uuid4().hex[:8]}@example.com"
    user_b_password = "SecurePassword123!"

    resp = client.post("/api/auth/signup", json={"email": user_b_email, "password": user_b_password})
    assert_status(resp, 201, "User B signup")
    token_b = resp.json()["access_token"]
    auth_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User A creates shelves
    log_step("3. User A creates custom shelves")
    resp = client.post("/api/shelves", headers=auth_a, json={"name": "Favorites"})
    assert_status(resp, 201, "User A creates 'Favorites'")
    fav_shelf = resp.json()
    fav_shelf_id = fav_shelf["id"]
    assert fav_shelf["name"] == "Favorites"
    assert fav_shelf["book_count"] == 0

    resp = client.post("/api/shelves", headers=auth_a, json={"name": "Sci-Fi"})
    assert_status(resp, 201, "User A creates 'Sci-Fi'")
    scifi_shelf = resp.json()
    scifi_shelf_id = scifi_shelf["id"]

    # 4. Duplicate shelf name enforcement (409 Conflict)
    log_step("4. Duplicate shelf name enforcement (409 Conflict)")
    resp = client.post("/api/shelves", headers=auth_a, json={"name": "Favorites"})
    assert_status(resp, 409, "User A cannot create duplicate 'Favorites' shelf")

    # Name with leading/trailing spaces should also be trimmed and rejected
    resp = client.post("/api/shelves", headers=auth_a, json={"name": "  Favorites  "})
    assert_status(resp, 409, "Trimmed duplicate shelf name rejected with 409")

    # Empty shelf name rejected
    resp = client.post("/api/shelves", headers=auth_a, json={"name": "   "})
    assert_status(resp, 422, "Empty shelf name rejected with 422")

    # 5. User B can create shelf with same name (User-level isolation)
    log_step("5. User-level shelf name isolation")
    resp = client.post("/api/shelves", headers=auth_b, json={"name": "Favorites"})
    assert_status(resp, 201, "User B can create shelf named 'Favorites' (isolated namespace)")
    b_fav_shelf_id = resp.json()["id"]

    # 6. User A creates books
    log_step("6. User A creates books in catalog")
    resp = client.post("/api/books", headers=auth_a, json={"title": "Dune", "author": "Frank Herbert", "total_pages": 600})
    assert_status(resp, 201, "User A creates Book 1 (Dune)")
    book_1 = resp.json()
    book_1_id = book_1["id"]

    resp = client.post("/api/books", headers=auth_a, json={"title": "Neuromancer", "author": "William Gibson", "total_pages": 300})
    assert_status(resp, 201, "User A creates Book 2 (Neuromancer)")
    book_2 = resp.json()
    book_2_id = book_2["id"]

    # 7. Add books to shelves (Many-to-Many)
    log_step("7. Many-to-Many Book Assignment")
    # Book 1 into Favorites
    resp = client.post(f"/api/shelves/{fav_shelf_id}/books", headers=auth_a, json={"book_id": book_1_id})
    assert_status(resp, 201, "User A adds Dune to Favorites")

    # Book 1 also into Sci-Fi (single book on multiple shelves)
    resp = client.post(f"/api/shelves/{scifi_shelf_id}/books", headers=auth_a, json={"book_id": book_1_id})
    assert_status(resp, 201, "User A adds Dune to Sci-Fi (same book, multiple shelves)")

    # Book 2 into Sci-Fi (multiple books on single shelf)
    resp = client.post(f"/api/shelves/{scifi_shelf_id}/books", headers=auth_a, json={"book_id": book_2_id})
    assert_status(resp, 201, "User A adds Neuromancer to Sci-Fi")

    # 8. Duplicate book on same shelf rejection (409 Conflict)
    log_step("8. Duplicate book on same shelf rejection (409 Conflict)")
    resp = client.post(f"/api/shelves/{fav_shelf_id}/books", headers=auth_a, json={"book_id": book_1_id})
    assert_status(resp, 409, "Adding duplicate book to Favorites rejected with 409")

    # 9. Verify shelf listing and book counts
    log_step("9. Shelf listing with accurate book_count")
    resp = client.get("/api/shelves", headers=auth_a)
    assert_status(resp, 200, "User A lists shelves")
    shelves_data = resp.json()
    shelf_map = {s["id"]: s for s in shelves_data}
    assert shelf_map[fav_shelf_id]["book_count"] == 1, f"Expected 1, got {shelf_map[fav_shelf_id]['book_count']}"
    assert shelf_map[scifi_shelf_id]["book_count"] == 2, f"Expected 2, got {shelf_map[scifi_shelf_id]['book_count']}"
    print("[OK] Shelf book counts verified: Favorites=1, Sci-Fi=2")

    # 10. Verify shelf detail endpoint
    log_step("10. Shelf detail endpoint")
    resp = client.get(f"/api/shelves/{scifi_shelf_id}", headers=auth_a)
    assert_status(resp, 200, "User A gets Sci-Fi shelf detail")
    detail = resp.json()
    assert detail["book_count"] == 2
    assert len(detail["books"]) == 2
    titles = [b["title"] for b in detail["books"]]
    assert "Dune" in titles and "Neuromancer" in titles
    print("[OK] Shelf detail returned correct books list")

    # 11. Filter catalog by shelf_id
    log_step("11. Filter catalog by shelf_id")
    resp = client.get(f"/api/books?shelf_id={fav_shelf_id}", headers=auth_a)
    assert_status(resp, 200, "Filter books by Favorites shelf")
    fav_books = resp.json()
    assert len(fav_books) == 1
    assert fav_books[0]["title"] == "Dune"

    resp = client.get(f"/api/books?shelf_id={scifi_shelf_id}", headers=auth_a)
    assert_status(resp, 200, "Filter books by Sci-Fi shelf")
    scifi_books = resp.json()
    assert len(scifi_books) == 2

    # 12. Cross-user isolation checks
    log_step("12. Cross-user security and isolation")
    # User B cannot view User A's shelf
    resp = client.get(f"/api/shelves/{fav_shelf_id}", headers=auth_b)
    assert_status(resp, 404, "User B cannot view User A's shelf (404)")

    # User B cannot update User A's shelf
    resp = client.patch(f"/api/shelves/{fav_shelf_id}", headers=auth_b, json={"name": "Hacked"})
    assert_status(resp, 404, "User B cannot rename User A's shelf (404)")

    # User B cannot delete User A's shelf
    resp = client.delete(f"/api/shelves/{fav_shelf_id}", headers=auth_b)
    assert_status(resp, 404, "User B cannot delete User A's shelf (404)")

    # User B cannot filter books by User A's shelf
    resp = client.get(f"/api/books?shelf_id={fav_shelf_id}", headers=auth_b)
    assert_status(resp, 404, "User B cannot filter books using User A's shelf_id (404)")

    # User B cannot add User A's book to User B's shelf
    resp = client.post(f"/api/shelves/{b_fav_shelf_id}/books", headers=auth_b, json={"book_id": book_1_id})
    assert_status(resp, 404, "User B cannot add User A's book to their own shelf (404)")

    # User A cannot add a non-existent book
    resp = client.post(f"/api/shelves/{fav_shelf_id}/books", headers=auth_a, json={"book_id": str(uuid.uuid4())})
    assert_status(resp, 404, "Adding non-existent book returns 404")

    # 13. Rename shelf
    log_step("13. Rename custom shelf")
    resp = client.patch(f"/api/shelves/{scifi_shelf_id}", headers=auth_a, json={"name": "Cyberpunk & Sci-Fi"})
    assert_status(resp, 200, "User A renames 'Sci-Fi' to 'Cyberpunk & Sci-Fi'")
    assert resp.json()["name"] == "Cyberpunk & Sci-Fi"

    # Rename conflict check
    resp = client.patch(f"/api/shelves/{scifi_shelf_id}", headers=auth_a, json={"name": "Favorites"})
    assert_status(resp, 409, "Renaming to existing shelf name fails with 409 Conflict")

    # 14. Remove book from shelf
    log_step("14. Remove book from shelf")
    resp = client.delete(f"/api/shelves/{scifi_shelf_id}/books/{book_1_id}", headers=auth_a)
    assert_status(resp, 204, "Remove Dune from Cyberpunk & Sci-Fi")

    # Removing again returns 404
    resp = client.delete(f"/api/shelves/{scifi_shelf_id}/books/{book_1_id}", headers=auth_a)
    assert_status(resp, 404, "Removing non-present book from shelf returns 404")

    # Verify Dune is still in personal library
    resp = client.get(f"/api/books/{book_1_id}", headers=auth_a)
    assert_status(resp, 200, "Dune still exists in user library after removal from shelf")

    # Verify Dune is still on Favorites shelf
    resp = client.get(f"/api/shelves/{fav_shelf_id}", headers=auth_a)
    assert_status(resp, 200, "Fetch Favorites detail")
    assert resp.json()["book_count"] == 1
    assert resp.json()["books"][0]["id"] == book_1_id

    # 15. Delete shelf and verify cascade safety
    log_step("15. Delete shelf cascade safety")
    resp = client.delete(f"/api/shelves/{fav_shelf_id}", headers=auth_a)
    assert_status(resp, 204, "Delete Favorites shelf")

    # Verify shelf is gone
    resp = client.get(f"/api/shelves/{fav_shelf_id}", headers=auth_a)
    assert_status(resp, 404, "Favorites shelf is 404 after deletion")

    # CRITICAL: Verify Dune is STILL in user library
    resp = client.get(f"/api/books/{book_1_id}", headers=auth_a)
    assert_status(resp, 200, "Dune is PRESERVED in library after shelf deletion (CASCADE SAFETY CONFIRMED)")

    print("\n========================================================")
    print("ALL PHASE 4 BACKEND TESTS PASSED SUCCESSFULLY! [OK]")
    print("========================================================\n")


if __name__ == "__main__":
    run_tests()
