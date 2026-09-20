"""
Comprehensive Phase 9 Automated Test Suite for BookNest:
Real-time WebSocket Updates (python-socketio)

Verifies:
1. Handshake Auth Rejection (No Token): Connection refused without token.
2. Handshake Auth Rejection (Invalid Token): Connection refused with bad JWT.
3. Handshake Auth Rejection (Refresh Token): Refresh token rejected in handshake (access token only).
4. Handshake Auth Success: Valid access token connects; user joined to personal room.
5. Book CRUD Live Broadcast: REST book creation emits 'book_added' to creator's socket.
6. Multi-User Isolation: User B's socket does NOT receive User A's private book addition.
7. Reading Progress Live Broadcast: Progress update emits 'progress_updated' with milestone data.
8. Shared Shelf Collaboration Live Sync: User A adds book to shared shelf -> User B receives 'shelf_book_added'.
9. Shelf Room Revocation (Safeguard 2):
   - When User A removes User B from shelf, User B's socket is detached from shelf room.
   - User B receives 'shelf_access_revoked' event.
   - Future shelf events are NOT delivered to User B.
   - User B attempting to rejoin shelf is rejected with authorization error.
10. Peer-to-Peer Lending Live Sync:
   - Lending book to User B emits 'book_lent' to User B's socket.
   - Returning book emits 'book_returned' to User B's socket.
11. Activity Feed Live Sync: Participants receive 'activity_created' events.
"""
import asyncio
import sys
import uuid
import httpx
import socketio

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_HTTP_URL = "http://localhost:8000/api"
SOCKET_URL = "http://localhost:8000"


def log_step(step_num: int, title: str):
    print(f"\n[{step_num}/11] {title}")


async def create_user(client: httpx.AsyncClient, name: str, email: str, password: str = "TestPass123!"):
    resp = await client.post(
        f"{BASE_HTTP_URL}/auth/signup",
        json={"name": name, "email": email, "password": password},
    )
    assert resp.status_code == 201, f"Failed to register user: {resp.text}"
    data = resp.json()
    return data["user"], data["access_token"], resp.cookies.get("refresh_token")


async def run_tests():
    print("=== Phase 9: Starting Real-time WebSocket Updates Test Suite ===")
    
    async with httpx.AsyncClient(timeout=15.0) as http_client:
        uid = uuid.uuid4().hex[:6]
        user_a, token_a, refresh_a = await create_user(http_client, "User Alpha", f"alpha_{uid}@example.com")
        user_b, token_b, refresh_b = await create_user(http_client, "User Beta", f"beta_{uid}@example.com")
        user_c, token_c, _ = await create_user(http_client, "User Gamma", f"gamma_{uid}@example.com")
        print("  [Setup OK] Registered 3 test users.")

        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # -----------------------------------------------------------------
        # Step 1: Handshake Auth Rejection (No Token)
        # -----------------------------------------------------------------
        log_step(1, "Handshake Auth Rejection: No auth token")
        sio_unauth = socketio.AsyncClient()
        rejected = False
        try:
            await sio_unauth.connect(SOCKET_URL, socketio_path="socket.io", wait_timeout=3)
        except Exception:
            rejected = True
        finally:
            if sio_unauth.connected:
                await sio_unauth.disconnect()
        assert rejected, "Expected connection without auth to be rejected!"
        print("  [PASS] Connection refused when no auth token is provided.")

        # -----------------------------------------------------------------
        # Step 2: Handshake Auth Rejection (Invalid Token)
        # -----------------------------------------------------------------
        log_step(2, "Handshake Auth Rejection: Invalid/corrupt token")
        sio_bad = socketio.AsyncClient()
        rejected_bad = False
        try:
            await sio_bad.connect(
                SOCKET_URL,
                socketio_path="socket.io",
                auth={"token": "bad.invalid.jwt.token"},
                wait_timeout=3,
            )
        except Exception:
            rejected_bad = True
        finally:
            if sio_bad.connected:
                await sio_bad.disconnect()
        assert rejected_bad, "Expected bad token connection to be rejected!"
        print("  [PASS] Connection refused with invalid JWT token.")

        # -----------------------------------------------------------------
        # Step 3: Handshake Auth Rejection (Refresh Token rejected)
        # -----------------------------------------------------------------
        log_step(3, "Handshake Auth Rejection: Refresh token rejected (Safeguard 6)")
        sio_refresh = socketio.AsyncClient()
        rejected_refresh = False
        try:
            # Attempt connection with raw refresh token string
            await sio_refresh.connect(
                SOCKET_URL,
                socketio_path="socket.io",
                auth={"token": refresh_a or "mock_refresh_token"},
                wait_timeout=3,
            )
        except Exception:
            rejected_refresh = True
        finally:
            if sio_refresh.connected:
                await sio_refresh.disconnect()
        assert rejected_refresh, "Expected refresh token to be rejected in WebSocket handshake!"
        print("  [PASS] Refresh token safely rejected in WebSocket handshake.")

        # -----------------------------------------------------------------
        # Step 4: Handshake Auth Success
        # -----------------------------------------------------------------
        log_step(4, "Handshake Auth Success: Valid access token connects")
        sio_a = socketio.AsyncClient()
        sio_b = socketio.AsyncClient()

        # Queues to capture events for assertions
        events_a = asyncio.Queue()
        events_b = asyncio.Queue()

        @sio_a.on("*")
        async def on_any_a(event, data):
            await events_a.put((event, data))

        @sio_b.on("*")
        async def on_any_b(event, data):
            await events_b.put((event, data))

        await sio_a.connect(
            SOCKET_URL,
            socketio_path="socket.io",
            auth={"token": token_a},
            wait_timeout=5,
        )
        await sio_b.connect(
            SOCKET_URL,
            socketio_path="socket.io",
            auth={"token": token_b},
            wait_timeout=5,
        )

        assert sio_a.connected, "Socket A failed to connect"
        assert sio_b.connected, "Socket B failed to connect"
        print(f"  [PASS] Socket A connected (sid={sio_a.sid}), Socket B connected (sid={sio_b.sid})")

        # -----------------------------------------------------------------
        # Step 5 & 6: Book CRUD Live Broadcast & Multi-User Isolation
        # -----------------------------------------------------------------
        log_step(5, "Book CRUD Live Broadcast & Isolation check")
        resp = await http_client.post(
            f"{BASE_HTTP_URL}/books",
            headers=headers_a,
            json={
                "title": "Realtime Magic",
                "author": "Socket Master",
                "status": "reading",
                "total_pages": 200,
                "current_page": 20,
            },
        )
        assert resp.status_code == 201
        book_a = resp.json()
        book_a_id = book_a["id"]

        # User A should receive 'book_added' and 'activity_created'
        received_book_added = False
        for _ in range(5):
            try:
                ev, data = await asyncio.wait_for(events_a.get(), timeout=2.0)
                if ev == "book_added" and data.get("book", {}).get("id") == book_a_id:
                    received_book_added = True
                    break
            except asyncio.TimeoutError:
                break
        assert received_book_added, "User A socket did not receive 'book_added' event!"
        print("  [PASS] User A received 'book_added' event live.")

        log_step(6, "Multi-User Isolation: User B does NOT receive User A's private book")
        b_received_private = False
        try:
            while not events_b.empty():
                ev, data = events_b.get_nowait()
                if ev == "book_added" and data.get("book", {}).get("id") == book_a_id:
                    b_received_private = True
        except Exception:
            pass
        assert not b_received_private, "User B leaked User A's private book_added event!"
        print("  [PASS] User B socket did not receive User A's private book event.")

        # -----------------------------------------------------------------
        # Step 7: Reading Progress Live Broadcast
        # -----------------------------------------------------------------
        log_step(7, "Reading Progress Live Broadcast with Milestones")
        resp = await http_client.post(
            f"{BASE_HTTP_URL}/books/{book_a_id}/progress",
            headers=headers_a,
            json={"current_page": 100, "notes": "Halfway there!"},  # 50% milestone: half
        )
        assert resp.status_code == 200

        received_progress = False
        for _ in range(5):
            try:
                ev, data = await asyncio.wait_for(events_a.get(), timeout=2.0)
                if ev == "progress_updated" and data.get("book", {}).get("current_page") == 100:
                    assert data.get("milestone") == "half"
                    received_progress = True
                    break
            except asyncio.TimeoutError:
                break
        assert received_progress, "User A socket did not receive 'progress_updated' with milestone!"
        print("  [PASS] User A received 'progress_updated' with milestone='half'.")

        # -----------------------------------------------------------------
        # Step 8: Shared Shelf Collaboration Live Sync
        # -----------------------------------------------------------------
        log_step(8, "Shared Shelf Collaboration: Real-time sync across members")
        # User A creates a shelf
        resp = await http_client.post(
            f"{BASE_HTTP_URL}/shelves",
            headers=headers_a,
            json={"name": f"Sci-Fi Collab {uid}"},
        )
        assert resp.status_code == 201
        shelf = resp.json()
        shelf_id = shelf["id"]

        # User A shares with User B as editor
        resp = await http_client.post(
            f"{BASE_HTTP_URL}/shelves/{shelf_id}/shares",
            headers=headers_a,
            json={"email": user_b["email"], "role": "editor"},
        )
        assert resp.status_code == 201
        share_record = resp.json()
        share_id = share_record["id"]

        # Both join shelf room
        res_join_a = await sio_a.call("join_shelf", {"shelf_id": shelf_id}, timeout=3)
        res_join_b = await sio_b.call("join_shelf", {"shelf_id": shelf_id}, timeout=3)
        assert res_join_a.get("status") == "ok", f"User A join_shelf failed: {res_join_a}"
        assert res_join_b.get("status") == "ok", f"User B join_shelf failed: {res_join_b}"

        # User A adds book to shelf via REST
        resp = await http_client.post(
            f"{BASE_HTTP_URL}/shelves/{shelf_id}/books",
            headers=headers_a,
            json={"book_id": book_a_id},
        )
        assert resp.status_code == 201

        # User B should receive 'shelf_book_added' in real time
        received_shelf_book_b = False
        for _ in range(5):
            try:
                ev, data = await asyncio.wait_for(events_b.get(), timeout=2.0)
                if ev == "shelf_book_added" and data.get("shelf_id") == shelf_id:
                    received_shelf_book_b = True
                    break
            except asyncio.TimeoutError:
                break
        assert received_shelf_book_b, "User B did not receive 'shelf_book_added' event!"
        print("  [PASS] User B received 'shelf_book_added' event in real time.")

        # -----------------------------------------------------------------
        # Step 9: Shelf Room Revocation (Safeguard 2)
        # -----------------------------------------------------------------
        log_step(9, "Shelf Room Revocation: Instant socket detachment upon removal")
        # Drain existing events in B
        while not events_b.empty():
            events_b.get_nowait()

        # User A removes User B from shelf via REST
        resp = await http_client.delete(
            f"{BASE_HTTP_URL}/shelves/{shelf_id}/shares/{share_id}",
            headers=headers_a,
        )
        assert resp.status_code == 204

        # User B should receive 'shelf_access_revoked'
        received_revoked = False
        for _ in range(5):
            try:
                ev, data = await asyncio.wait_for(events_b.get(), timeout=2.0)
                if ev == "shelf_access_revoked" and data.get("shelf_id") == shelf_id:
                    received_revoked = True
                    break
            except asyncio.TimeoutError:
                break
        assert received_revoked, "User B did not receive 'shelf_access_revoked' notification!"
        print("  [PASS] User B received 'shelf_access_revoked' event.")

        # Create Book A2 and add to shelf
        resp = await http_client.post(
            f"{BASE_HTTP_URL}/books",
            headers=headers_a,
            json={"title": "Secret Book 2", "author": "Author A", "status": "want_to_read"},
        )
        book_a2_id = resp.json()["id"]

        resp = await http_client.post(
            f"{BASE_HTTP_URL}/shelves/{shelf_id}/books",
            headers=headers_a,
            json={"book_id": book_a2_id},
        )
        assert resp.status_code == 201

        # User B must NOT receive this event now that they are revoked
        await asyncio.sleep(0.5)
        b_got_revoked_event = False
        while not events_b.empty():
            ev, data = events_b.get_nowait()
            if ev == "shelf_book_added" and data.get("book_id") == book_a2_id:
                b_got_revoked_event = True
        assert not b_got_revoked_event, "Revoked User B received a shelf event after removal!"
        print("  [PASS] Revoked User B did NOT receive post-removal shelf events.")

        # User B attempts to rejoin shelf room -> should be rejected
        res_rejoin = await sio_b.call("join_shelf", {"shelf_id": shelf_id}, timeout=3)
        assert res_rejoin.get("status") == "error", "Revoked user was incorrectly allowed to rejoin shelf room!"
        print("  [PASS] Revoked User B rejected on rejoin attempt (database re-check enforced).")

        # -----------------------------------------------------------------
        # Step 10: Peer-to-Peer Lending Live Sync
        # -----------------------------------------------------------------
        log_step(10, "Peer-to-Peer Lending: Live sync on lend and return")
        # Drain events_b
        while not events_b.empty():
            events_b.get_nowait()

        # User A lends Book A to User B
        resp = await http_client.post(
            f"{BASE_HTTP_URL}/lending",
            headers=headers_a,
            json={"book_id": book_a_id, "borrower_email": user_b["email"]},
        )
        assert resp.status_code == 201
        lending_rec = resp.json()
        lending_id = lending_rec["id"]

        # User B should receive 'book_lent'
        received_lent_b = False
        for _ in range(5):
            try:
                ev, data = await asyncio.wait_for(events_b.get(), timeout=2.0)
                if ev == "book_lent" and data.get("lending", {}).get("id") == lending_id:
                    received_lent_b = True
                    break
            except asyncio.TimeoutError:
                break
        assert received_lent_b, "User B did not receive 'book_lent' live event!"
        print("  [PASS] User B received 'book_lent' live event.")

        # User A returns book
        resp = await http_client.post(
            f"{BASE_HTTP_URL}/lending/{lending_id}/return",
            headers=headers_a,
        )
        assert resp.status_code == 200

        # User B should receive 'book_returned'
        received_returned_b = False
        for _ in range(5):
            try:
                ev, data = await asyncio.wait_for(events_b.get(), timeout=2.0)
                if ev == "book_returned" and data.get("lending", {}).get("id") == lending_id:
                    received_returned_b = True
                    break
            except asyncio.TimeoutError:
                break
        assert received_returned_b, "User B did not receive 'book_returned' live event!"
        print("  [PASS] User B received 'book_returned' live event.")

        # -----------------------------------------------------------------
        # Step 11: Activity Feed Live Sync
        # -----------------------------------------------------------------
        log_step(11, "Activity Feed Live Sync")
        # User A creating a new book generates an activity_created event
        while not events_a.empty():
            events_a.get_nowait()

        resp = await http_client.post(
            f"{BASE_HTTP_URL}/books",
            headers=headers_a,
            json={"title": "Activity Test Book", "author": "Tester", "status": "want_to_read"},
        )
        assert resp.status_code == 201

        received_activity_a = False
        for _ in range(5):
            try:
                ev, data = await asyncio.wait_for(events_a.get(), timeout=2.0)
                if ev == "activity_created" and data.get("activity", {}).get("action") == "book_added":
                    received_activity_a = True
                    break
            except asyncio.TimeoutError:
                break
        assert received_activity_a, "User A did not receive 'activity_created' event!"
        print("  [PASS] User A received 'activity_created' live event.")

        # Cleanup
        await sio_a.disconnect()
        await sio_b.disconnect()
        print("\n=== Phase 9: All 11 Automated Real-time WebSocket Tests PASSED! ===")


if __name__ == "__main__":
    asyncio.run(run_tests())
