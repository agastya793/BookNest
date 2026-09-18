import asyncio
import sys
import httpx

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://localhost:8000/api"

async def run_tests():
    print("=== Starting Phase 3 Book Management & Personal Library CRUD Tests ===\n")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Setup: Create two separate users for isolation testing
        ts = int(asyncio.get_event_loop().time() * 1000)
        user_a_email = f"user_a_{ts}@example.com"
        user_b_email = f"user_b_{ts}@example.com"

        res_a = await client.post("/auth/signup", json={
            "name": "User Alpha", "email": user_a_email, "password": "Pass@Word123"
        })
        assert res_a.status_code == 201
        token_a = res_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        res_b = await client.post("/auth/signup", json={
            "name": "User Beta", "email": user_b_email, "password": "Pass@Word123"
        })
        assert res_b.status_code == 201
        token_b = res_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}
        print("   [OK] Created User A and User B for isolation testing")

        # Test 1: Create book with valid fields
        print("\n1. Testing book creation...")
        res = await client.post("/books", headers=headers_a, json={
            "title": "The Hobbit",
            "author": "J.R.R. Tolkien",
            "status": "want_to_read",
            "total_pages": 310,
            "current_page": 0,
            "notes": "Classic fantasy",
        })
        assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.text}"
        book1 = res.json()
        assert book1["title"] == "The Hobbit"
        assert book1["author"] == "J.R.R. Tolkien"
        assert book1["status"] == "want_to_read"
        assert book1["total_pages"] == 310
        assert book1["current_page"] == 0
        assert book1["progress_percentage"] == 0.0
        assert book1["finished_date"] is None
        book1_id = book1["id"]
        print(f"   [OK] Created book '{book1['title']}' with progress 0.0%")

        # Test 2: Input validation and model_validator rules
        print("\n2. Testing cross-field and boundary validations...")
        # 2a: current_page > total_pages
        res = await client.post("/books", headers=headers_a, json={
            "title": "Bad Pages",
            "author": "Author",
            "total_pages": 100,
            "current_page": 150,
        })
        assert res.status_code == 422, f"Expected 422 for current_page > total_pages, got {res.status_code}"
        print("   [OK] Rejected current_page > total_pages (422)")

        # 2b: Negative current_page
        res = await client.post("/books", headers=headers_a, json={
            "title": "Negative Page",
            "author": "Author",
            "current_page": -1,
        })
        assert res.status_code == 422, f"Expected 422 for negative current_page, got {res.status_code}"
        print("   [OK] Rejected negative current_page (422)")

        # 2c: Rating outside 1-5
        res = await client.post("/books", headers=headers_a, json={
            "title": "Bad Rating",
            "author": "Author",
            "rating": 6,
        })
        assert res.status_code == 422, f"Expected 422 for rating > 5, got {res.status_code}"
        print("   [OK] Rejected invalid rating > 5 (422)")

        # 2d: Invalid status
        res = await client.post("/books", headers=headers_a, json={
            "title": "Bad Status",
            "author": "Author",
            "status": "abandoned",
        })
        assert res.status_code == 422, f"Expected 422 for invalid status, got {res.status_code}"
        print("   [OK] Rejected invalid status (422)")

        # Test 3: Finished status behavior on creation
        print("\n3. Testing finished status behavior on creation...")
        res = await client.post("/books", headers=headers_a, json={
            "title": "Dune",
            "author": "Frank Herbert",
            "status": "finished",
            "total_pages": 412,
            "current_page": 0,
            "rating": 5,
        })
        assert res.status_code == 201
        dune = res.json()
        assert dune["status"] == "finished"
        assert dune["finished_date"] is not None, "finished_date should be automatically set"
        assert dune["current_page"] == 412, "current_page should be auto-completed to total_pages"
        assert dune["progress_percentage"] == 100.0
        print("   [OK] Finished book auto-completed pages to 412 and set finished_date")

        # Test 4: Books without total_pages have progress_percentage as null
        print("\n4. Testing progress_percentage with null total_pages...")
        res = await client.post("/books", headers=headers_a, json={
            "title": "Audiobook Without Pages",
            "author": "Narrator",
            "status": "reading",
        })
        assert res.status_code == 201
        no_pages = res.json()
        assert no_pages["total_pages"] is None
        assert no_pages["progress_percentage"] is None, "Expected progress_percentage to be None"
        print("   [OK] progress_percentage correctly null when total_pages is absent")

        # Test 5: List books with filtering, search, and sorting
        print("\n5. Testing list_books, search, and sorting...")
        # Create additional book
        await client.post("/books", headers=headers_a, json={
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "status": "reading",
            "total_pages": 450,
            "current_page": 150,
            "rating": 5,
        })

        # 5a: Filter by status
        res = await client.get("/books?status=reading", headers=headers_a)
        assert res.status_code == 200
        data_5a = res.json()
        reading_books = data_5a.get("items", data_5a)
        assert all(b["status"] == "reading" for b in reading_books)
        print(f"   [OK] Status filter returned {len(reading_books)} reading books")

        # 5b: Search by author
        res = await client.get("/books?search=Martin", headers=headers_a)
        assert res.status_code == 200
        data_5b = res.json()
        search_res = data_5b.get("items", data_5b)
        assert any(b["title"] == "Clean Code" for b in search_res)
        print("   [OK] Search filter successfully matched author 'Robert C. Martin'")

        # 5c: Sorting by title asc
        res = await client.get("/books?sort_by=title&sort_dir=asc", headers=headers_a)
        assert res.status_code == 200
        data_5c = res.json()
        titles = [b["title"] for b in data_5c.get("items", data_5c)]
        assert titles == sorted(titles), "Books should be sorted ascending by title"
        print("   [OK] Standardized sorting (sort_by=title&sort_dir=asc) validated")

        # Test 6: Strict multi-user data isolation
        print("\n6. Testing multi-user data isolation...")
        # User B tries to view User A's book
        res = await client.get(f"/books/{book1_id}", headers=headers_b)
        assert res.status_code == 404, f"Expected 404 when User B accesses User A's book, got {res.status_code}"
        print("   [OK] User B received 404 when requesting User A's book")

        # User B tries to patch User A's book
        res = await client.patch(f"/books/{book1_id}", headers=headers_b, json={"rating": 1})
        assert res.status_code == 404, f"Expected 404 when User B patches User A's book, got {res.status_code}"
        print("   [OK] User B received 404 when trying to PATCH User A's book")

        # User B tries to delete User A's book
        res = await client.delete(f"/books/{book1_id}", headers=headers_b)
        assert res.status_code == 404, f"Expected 404 when User B deletes User A's book, got {res.status_code}"
        print("   [OK] User B received 404 when trying to DELETE User A's book")

        # User B list does not contain User A's books
        res = await client.get("/books", headers=headers_b)
        assert res.status_code == 200
        data_b = res.json()
        assert len(data_b.get("items", data_b)) == 0, "User B should have an empty library"
        print("   [OK] User B library is empty and completely isolated from User A")

        # Test 7: Cross-field merge validation during PATCH
        print("\n7. Testing cross-field merge validation on partial PATCH...")
        # book1 has total_pages = 310. Try patching current_page to 400.
        res = await client.patch(f"/books/{book1_id}", headers=headers_a, json={"current_page": 400})
        assert res.status_code == 422, f"Expected 422 for current_page exceeding existing total_pages, got {res.status_code}"
        print("   [OK] PATCH current_page (400) > existing total_pages (310) rejected with 422")

        # Valid partial update
        res = await client.patch(f"/books/{book1_id}", headers=headers_a, json={"current_page": 155})
        assert res.status_code == 200
        updated_book1 = res.json()
        assert updated_book1["current_page"] == 155
        assert updated_book1["progress_percentage"] == 50.0
        print("   [OK] Valid PATCH updated current_page to 155 (50.0% progress)")

        # Test 8: Status transition on update
        print("\n8. Testing status transition finished_date lifecycle...")
        # Change book1 to finished
        res = await client.patch(f"/books/{book1_id}", headers=headers_a, json={"status": "finished"})
        assert res.status_code == 200
        finished_book1 = res.json()
        assert finished_book1["status"] == "finished"
        assert finished_book1["finished_date"] is not None
        assert finished_book1["current_page"] == 310, "current_page should auto-complete to total_pages (310)"
        print("   [OK] Transition to 'finished' auto-set finished_date and completed current_page to 310")

        # Revert book1 from finished to reading
        res = await client.patch(f"/books/{book1_id}", headers=headers_a, json={"status": "reading"})
        assert res.status_code == 200
        reverted_book1 = res.json()
        assert reverted_book1["status"] == "reading"
        assert reverted_book1["finished_date"] is None, "finished_date should be cleared when status reverts"
        print("   [OK] Reverting from 'finished' to 'reading' cleared finished_date")

        # Test 9: PUT endpoint compatibility
        print("\n9. Testing PUT endpoint compatibility...")
        res = await client.put(f"/books/{book1_id}", headers=headers_a, json={
            "title": "The Hobbit: 75th Anniversary Edition",
            "rating": 5,
        })
        assert res.status_code == 200
        assert res.json()["title"] == "The Hobbit: 75th Anniversary Edition"
        assert res.json()["rating"] == 5
        print("   [OK] PUT endpoint updated book successfully")

        # Test 10: Delete book
        print("\n10. Testing book deletion...")
        res = await client.delete(f"/books/{book1_id}", headers=headers_a)
        assert res.status_code == 204
        print("   [OK] DELETE returned 204 No Content")

        # Confirm 404 after deletion
        res = await client.get(f"/books/{book1_id}", headers=headers_a)
        assert res.status_code == 404
        print("   [OK] Subsequent GET returned 404 Not Found")

    print("\nALL 10 PHASE 3 BACKEND TESTS PASSED FLAWLESSLY!")

if __name__ == "__main__":
    asyncio.run(run_tests())
