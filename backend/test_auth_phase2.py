import asyncio
import httpx
import sys

# Ensure UTF-8 output encoding on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_URL = "http://localhost:8000/api/auth"

async def run_tests():
    print("=== Starting Phase 2 Backend Auth Verification ===\n")
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Test 1: Password validation checks
        print("1. Testing password validation rules...")
        # 1a. Too short (< 8 chars)
        res = await client.post("/signup", json={"name": "Short", "email": "short@test.com", "password": "Sh1!"})
        assert res.status_code == 422, f"Expected 422 for short password, got {res.status_code}: {res.text}"
        print("   [OK] Rejected password < 8 characters (422)")

        # 1b. Missing uppercase
        res = await client.post("/signup", json={"name": "NoUpper", "email": "upper@test.com", "password": "password123!"})
        assert res.status_code == 422, f"Expected 422, got {res.status_code}: {res.text}"
        print("   [OK] Rejected password with no uppercase (422)")

        # 1c. Missing special char
        res = await client.post("/signup", json={"name": "NoSpecial", "email": "special@test.com", "password": "Password123"})
        assert res.status_code == 422, f"Expected 422, got {res.status_code}: {res.text}"
        print("   [OK] Rejected password with no special character (422)")

        # 1d. Exceeding 72 bytes (bcrypt limit)
        long_pw = "P@ssword1" + "a" * 70
        res = await client.post("/signup", json={"name": "TooLong", "email": "long@test.com", "password": long_pw})
        assert res.status_code == 422, f"Expected 422 for >72 byte password, got {res.status_code}: {res.text}"
        assert "72 bytes" in res.text, f"Expected message mentioning 72 bytes, got: {res.text}"
        print("   [OK] Rejected password exceeding 72 bytes (422)")

        # Test 2: Successful signup
        print("\n2. Testing successful user registration...")
        test_email = f"alice_{int(asyncio.get_event_loop().time() * 1000)}@example.com"
        res = await client.post("/signup", json={
            "name": "Alice Reader",
            "email": test_email,
            "password": "BookNest@Pass123"
        })
        assert res.status_code == 201, f"Expected 201 Created, got {res.status_code}: {res.text}"
        signup_data = res.json()
        assert "access_token" in signup_data, "Missing access_token in signup body"
        assert "user" in signup_data, "Missing user in signup body"
        assert signup_data["user"]["email"] == test_email
        assert "password_hash" not in signup_data["user"]
        assert "refresh_token" in res.cookies, "Missing refresh_token in response cookies"
        print(f"   [OK] User registered successfully ({signup_data['user']['name']}, id: {signup_data['user']['id']})")
        print(f"   [OK] Access token returned in JSON body")
        print(f"   [OK] Refresh token returned in HttpOnly cookie: {res.cookies['refresh_token'][:15]}...")

        # Test 3: Duplicate signup rejection (409 Conflict)
        print("\n3. Testing duplicate email registration...")
        res = await client.post("/signup", json={
            "name": "Alice Impostor",
            "email": test_email,
            "password": "BookNest@Pass123"
        })
        assert res.status_code == 409, f"Expected 409 Conflict, got {res.status_code}: {res.text}"
        print("   [OK] Rejected duplicate email with 409 Conflict")

        # Test 4: Login
        print("\n4. Testing login...")
        # 4a. Wrong password
        res = await client.post("/login", json={"email": test_email, "password": "WrongPassword1!"})
        assert res.status_code == 401, f"Expected 401 for wrong password, got {res.status_code}"
        print("   [OK] Rejected invalid password with 401 Unauthorized")

        # 4b. Correct password
        res = await client.post("/login", json={"email": test_email, "password": "BookNest@Pass123"})
        assert res.status_code == 200, f"Expected 200 OK, got {res.status_code}: {res.text}"
        login_data = res.json()
        access_token = login_data["access_token"]
        refresh_cookie_1 = res.cookies["refresh_token"]
        print("   [OK] Successful login with valid credentials")

        # Test 5: Protected profile /me
        print("\n5. Testing protected /api/auth/me endpoint...")
        # 5a. Unauthenticated
        res = await client.get("/me")
        assert res.status_code == 401, f"Expected 401, got {res.status_code}"
        print("   [OK] Unauthenticated request rejected with 401")

        # 5b. Authenticated with Bearer token
        res = await client.get("/me", headers={"Authorization": f"Bearer {access_token}"})
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        me_data = res.json()
        assert me_data["email"] == test_email
        assert "password_hash" not in me_data
        print(f"   [OK] Authenticated profile fetched: {me_data['name']} ({me_data['email']})")

        # Test 6: Refresh token rotation
        print("\n6. Testing refresh token rotation (single-use)...")
        res = await client.post("/refresh", cookies={"refresh_token": refresh_cookie_1})
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        refresh_cookie_2 = res.cookies["refresh_token"]
        new_access_token = res.json()["access_token"]
        assert refresh_cookie_2 != refresh_cookie_1, "Refresh token was not rotated to a new token!"
        print("   [OK] Refresh succeeded, new access token and rotated refresh token issued")

        # Test 7: Old refresh token re-use rejected (401)
        print("\n7. Testing re-use of old rotated refresh token...")
        res = await client.post("/refresh", cookies={"refresh_token": refresh_cookie_1})
        assert res.status_code == 401, f"Expected 401 for old token, got {res.status_code}"
        print("   [OK] Old rotated refresh token successfully rejected (401 Unauthorized)")

        # Test 8: Concurrent refresh test (Race Condition Safety)
        print("\n8. Testing concurrent refresh requests with same token (SELECT FOR UPDATE)...")
        # Launch two requests at the exact same moment with refresh_cookie_2
        task1 = client.post("/refresh", cookies={"refresh_token": refresh_cookie_2})
        task2 = client.post("/refresh", cookies={"refresh_token": refresh_cookie_2})
        res1, res2 = await asyncio.gather(task1, task2)

        statuses = sorted([res1.status_code, res2.status_code])
        assert statuses == [200, 401], f"Expected exactly one 200 and one 401, but got {statuses}"
        print(f"   [OK] Concurrent refresh results: {res1.status_code} and {res2.status_code}")
        print("   [OK] Exactly ONE request succeeded; the other received 401 Unauthorized!")

        # Determine which cookie is now the active one
        active_cookie = res1.cookies["refresh_token"] if res1.status_code == 200 else res2.cookies["refresh_token"]

        # Test 9: Logout & Revocation
        print("\n9. Testing logout and token revocation...")
        res = await client.post("/logout", cookies={"refresh_token": active_cookie})
        assert res.status_code == 200
        print("   [OK] Logout endpoint succeeded")

        # Verify revoked token cannot refresh
        res = await client.post("/refresh", cookies={"refresh_token": active_cookie})
        assert res.status_code == 401, f"Expected 401 for revoked token, got {res.status_code}"
        print("   [OK] Revoked token cannot refresh (401 Unauthorized)")

    print("\nALL 9 BACKEND AUTH TESTS PASSED FLAWLESSLY!")

if __name__ == "__main__":
    asyncio.run(run_tests())
