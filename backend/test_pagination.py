"""
Server-Side Pagination Test Suite for BookNest
Verifies:
1. page=1 returns only the requested page size
2. page=2 returns the next set of records (non-overlapping)
3. total is the count AFTER filters are applied
4. total_pages is correctly calculated
5. status + search + sorting + pagination work together
6. shelf_id + pagination work together
7. page beyond the last page returns an empty items list
8. User A cannot access User B's books through pagination (multi-user isolation)
"""
import asyncio
import sys
import uuid
import httpx

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://localhost:8000/api"


def log_step(title: str):
    print(f"\n=== {title} ===")


async def run_tests():
    print("=== Starting Server-Side Pagination Test Suite ===\n")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=15.0) as client:
        # Setup: Create User A and User B
        ts = int(asyncio.get_event_loop().time() * 1000)
        user_a_email = f"pagi_user_a_{ts}@example.com"
        user_b_email = f"pagi_user_b_{ts}@example.com"

        res_a = await client.post("/auth/signup", json={
            "name": "Pagination User A", "email": user_a_email, "password": "Pass@Word123"
        })
        assert res_a.status_code == 201, f"User A signup failed: {res_a.text}"
        token_a = res_a.json()["access_token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        res_b = await client.post("/auth/signup", json={
            "name": "Pagination User B", "email": user_b_email, "password": "Pass@Word123"
        })
        assert res_b.status_code == 201, f"User B signup failed: {res_b.text}"
        token_b = res_b.json()["access_token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}
        print("   [OK] Created User A and User B for isolation testing")

        # Populate User A library with 7 distinct books
        # Books with different titles, authors, statuses, ratings
        book_definitions = [
            {"title": "Algorithms", "author": "Thomas Cormen", "status": "reading", "rating": 5, "total_pages": 1300, "current_page": 200},
            {"title": "Brave New World", "author": "Aldous Huxley", "status": "finished", "rating": 4, "total_pages": 311, "current_page": 311},
            {"title": "Clean Architecture", "author": "Robert C. Martin", "status": "reading", "rating": 5, "total_pages": 400, "current_page": 100},
            {"title": "Design Patterns", "author": "Erich Gamma", "status": "want_to_read", "rating": 4, "total_pages": 395, "current_page": 0},
            {"title": "Effective Python", "author": "Brett Slatkin", "status": "finished", "rating": 5, "total_pages": 300, "current_page": 300},
            {"title": "Foundation", "author": "Isaac Asimov", "status": "finished", "rating": 3, "total_pages": 255, "current_page": 255},
            {"title": "Galactic Empire", "author": "Isaac Asimov", "status": "want_to_read", "rating": 4, "total_pages": 280, "current_page": 0},
        ]

        user_a_book_ids = []
        for b_def in book_definitions:
            res = await client.post("/books", headers=headers_a, json=b_def)
            assert res.status_code == 201, f"Book creation failed: {res.text}"
            user_a_book_ids.append(res.json()["id"])
        print(f"   [OK] Created 7 books in User A library (Total: 7)")

        # Populate User B library with 3 books
        for i in range(3):
            res = await client.post("/books", headers=headers_b, json={
                "title": f"User B Private Book {i+1}", "author": "Author B", "status": "reading"
            })
            assert res.status_code == 201
        print("   [OK] Created 3 books in User B library (Total: 3)")

        # Create a shelf for User A and assign 3 books
        res_shelf = await client.post("/shelves", headers=headers_a, json={"name": "Computer Science"})
        assert res_shelf.status_code == 201
        cs_shelf_id = res_shelf.json()["id"]

        # Assign Algorithms (index 0), Clean Architecture (index 2), Design Patterns (index 3)
        for idx in [0, 2, 3]:
            res_add = await client.post(f"/shelves/{cs_shelf_id}/books", headers=headers_a, json={"book_id": user_a_book_ids[idx]})
            assert res_add.status_code == 201
        print("   [OK] Created 'Computer Science' shelf for User A with 3 assigned books")

        # =====================================================================
        # 1. page=1 returns only the requested page size
        # =====================================================================
        log_step("1. page=1 returns only the requested page size")
        res = await client.get("/books?page=1&page_size=3", headers=headers_a)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert "items" in data, "Response must include 'items' array"
        assert "page" in data and data["page"] == 1, f"Expected page 1, got {data.get('page')}"
        assert "page_size" in data and data["page_size"] == 3, f"Expected page_size 3, got {data.get('page_size')}"
        assert len(data["items"]) == 3, f"Expected exactly 3 items for page_size=3, got {len(data['items'])}"
        page_1_ids = [b["id"] for b in data["items"]]
        print(f"   [OK] page=1 returned exactly 3 items: {[b['title'] for b in data['items']]}")

        # =====================================================================
        # 2. page=2 returns the next set of records
        # =====================================================================
        log_step("2. page=2 returns the next set of records")
        res = await client.get("/books?page=2&page_size=3", headers=headers_a)
        assert res.status_code == 200
        data_p2 = res.json()
        assert data_p2["page"] == 2
        assert len(data_p2["items"]) == 3, f"Expected 3 items on page 2, got {len(data_p2['items'])}"
        page_2_ids = [b["id"] for b in data_p2["items"]]

        # Verify page 1 and page 2 are disjoint
        overlap = set(page_1_ids).intersection(set(page_2_ids))
        assert len(overlap) == 0, f"Pages must not overlap, but found overlapping IDs: {overlap}"
        print(f"   [OK] page=2 returned next 3 distinct items: {[b['title'] for b in data_p2['items']]}")

        # Page 3 should return the 7th item
        res = await client.get("/books?page=3&page_size=3", headers=headers_a)
        assert res.status_code == 200
        data_p3 = res.json()
        assert len(data_p3["items"]) == 1, f"Expected 1 item on page 3, got {len(data_p3['items'])}"
        print(f"   [OK] page=3 returned final 1 item: {[b['title'] for b in data_p3['items']]}")

        # =====================================================================
        # 3. total is the count AFTER filters are applied
        # =====================================================================
        log_step("3. total is the count AFTER filters are applied")
        # Status filter: finished (3 books: Brave New World, Effective Python, Foundation)
        res = await client.get("/books?status=finished&page=1&page_size=2", headers=headers_a)
        assert res.status_code == 200
        data_finished = res.json()
        assert data_finished["total"] == 3, f"Expected total=3 for finished books, got {data_finished['total']}"
        assert data_finished["total_pages"] == 2, f"Expected total_pages=2 (3 items / 2 per page), got {data_finished['total_pages']}"
        assert len(data_finished["items"]) == 2
        assert all(b["status"] == "finished" for b in data_finished["items"])
        print("   [OK] Total count reflects status-filtered records (total=3, total_pages=2)")

        # Search filter: "Asimov" (2 books: Foundation, Galactic Empire)
        res = await client.get("/books?search=Asimov&page=1&page_size=10", headers=headers_a)
        assert res.status_code == 200
        data_search = res.json()
        assert data_search["total"] == 2, f"Expected total=2 for author 'Asimov', got {data_search['total']}"
        assert len(data_search["items"]) == 2
        assert all("Asimov" in b["author"] for b in data_search["items"])
        print("   [OK] Total count reflects search-filtered records (total=2)")

        # =====================================================================
        # 4. total_pages is correct
        # =====================================================================
        log_step("4. total_pages is correct across different page sizes")
        test_cases = [
            (1, 7),  # 7 / 1 = 7 pages
            (2, 4),  # ceil(7 / 2) = 4 pages
            (3, 3),  # ceil(7 / 3) = 3 pages
            (5, 2),  # ceil(7 / 5) = 2 pages
            (7, 1),  # ceil(7 / 7) = 1 page
            (10, 1), # ceil(7 / 10) = 1 page
        ]
        for p_size, exp_pages in test_cases:
            res = await client.get(f"/books?page=1&page_size={p_size}", headers=headers_a)
            assert res.status_code == 200
            d = res.json()
            assert d["total"] == 7
            assert d["total_pages"] == exp_pages, f"For page_size={p_size}, expected total_pages={exp_pages}, got {d['total_pages']}"
        print("   [OK] total_pages correctly calculated for page sizes 1, 2, 3, 5, 7, 10")

        # =====================================================================
        # 5. status + search + sorting + pagination work together
        # =====================================================================
        log_step("5. status + search + sorting + pagination combined")
        # Filter: reading (2 books: Algorithms, Clean Architecture), search: "a" (both match), sort by title asc
        res = await client.get("/books?status=reading&search=a&sort_by=title&sort_dir=asc&page=1&page_size=1", headers=headers_a)
        assert res.status_code == 200
        d_combo_1 = res.json()
        assert d_combo_1["total"] == 2
        assert d_combo_1["total_pages"] == 2
        assert len(d_combo_1["items"]) == 1
        assert d_combo_1["items"][0]["title"] == "Algorithms"

        # Page 2 of same combo
        res = await client.get("/books?status=reading&search=a&sort_by=title&sort_dir=asc&page=2&page_size=1", headers=headers_a)
        assert res.status_code == 200
        d_combo_2 = res.json()
        assert len(d_combo_2["items"]) == 1
        assert d_combo_2["items"][0]["title"] == "Clean Architecture"
        print("   [OK] Combined status + search + title sorting + pagination works seamlessly across pages")

        # Test date_added sorting
        res = await client.get("/books?sort_by=date_added&sort_dir=asc&page=1&page_size=3", headers=headers_a)
        assert res.status_code == 200
        d_date = res.json()
        assert len(d_date["items"]) == 3
        # First book added was Algorithms
        assert d_date["items"][0]["title"] == "Algorithms"
        print("   [OK] sort_by=date_added supported and sorted properly")

        # Test rating sorting
        res = await client.get("/books?sort_by=rating&sort_dir=desc&page=1&page_size=3", headers=headers_a)
        assert res.status_code == 200
        d_rating = res.json()
        assert all(b["rating"] == 5 for b in d_rating["items"])
        print("   [OK] sort_by=rating supported and sorted descending")

        # =====================================================================
        # 6. shelf_id + pagination work together
        # =====================================================================
        log_step("6. shelf_id + pagination work together")
        # CS Shelf has 3 books: Algorithms, Clean Architecture, Design Patterns
        res = await client.get(f"/books?shelf_id={cs_shelf_id}&page=1&page_size=2", headers=headers_a)
        assert res.status_code == 200
        d_shelf_p1 = res.json()
        assert d_shelf_p1["total"] == 3, f"Expected total=3 for shelf, got {d_shelf_p1['total']}"
        assert d_shelf_p1["total_pages"] == 2
        assert len(d_shelf_p1["items"]) == 2

        res = await client.get(f"/books?shelf_id={cs_shelf_id}&page=2&page_size=2", headers=headers_a)
        assert res.status_code == 200
        d_shelf_p2 = res.json()
        assert len(d_shelf_p2["items"]) == 1

        all_shelf_titles = [b["title"] for b in d_shelf_p1["items"]] + [b["title"] for b in d_shelf_p2["items"]]
        assert set(all_shelf_titles) == {"Algorithms", "Clean Architecture", "Design Patterns"}
        print(f"   [OK] shelf_id + pagination returned all 3 shelf books across pages: {all_shelf_titles}")

        # =====================================================================
        # 7. page beyond the last page returns an empty items list
        # =====================================================================
        log_step("7. page beyond the last page returns empty items list")
        res = await client.get("/books?page=999&page_size=10", headers=headers_a)
        assert res.status_code == 200
        d_beyond = res.json()
        assert d_beyond["items"] == [], f"Expected items=[], got {d_beyond['items']}"
        assert d_beyond["total"] == 7
        assert d_beyond["total_pages"] == 1
        assert d_beyond["page"] == 999
        assert d_beyond["page_size"] == 10
        print("   [OK] Page beyond last page returns empty items list with valid pagination metadata")

        # =====================================================================
        # 8. User A cannot access User B's books through pagination
        # =====================================================================
        log_step("8. Multi-user data isolation in pagination")
        # User B lists books
        res_b_list = await client.get("/books?page=1&page_size=10", headers=headers_b)
        assert res_b_list.status_code == 200
        d_b = res_b_list.json()
        assert d_b["total"] == 3, f"Expected User B total=3, got {d_b['total']}"
        b_book_ids = {b["id"] for b in d_b["items"]}
        a_book_ids = set(user_a_book_ids)
        assert b_book_ids.isdisjoint(a_book_ids), "User B library must not contain any of User A's books"

        # User A lists books
        res_a_list = await client.get("/books?page=1&page_size=100", headers=headers_a)
        assert res_a_list.status_code == 200
        d_a = res_a_list.json()
        assert d_a["total"] == 7
        curr_a_ids = {b["id"] for b in d_a["items"]}
        assert curr_a_ids.isdisjoint(b_book_ids), "User A library must not contain any of User B's books"

        # User B attempts to access User A's shelf via pagination
        res_b_shelf = await client.get(f"/books?shelf_id={cs_shelf_id}&page=1&page_size=10", headers=headers_b)
        assert res_b_shelf.status_code == 404, f"Expected 404 when User B uses User A's shelf_id, got {res_b_shelf.status_code}"
        print("   [OK] Strict multi-user isolation confirmed: User A and User B cannot access each other's books or shelves via pagination")

    print("\n========================================================")
    print("ALL 8 SERVER-SIDE PAGINATION TESTS PASSED FLAWLESSLY! [OK]")
    print("========================================================\n")


if __name__ == "__main__":
    asyncio.run(run_tests())
