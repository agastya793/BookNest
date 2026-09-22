# BookNest

A full-stack reading tracker with authentication, books, custom shelves, collaboration/RBAC, reading progress, peer-to-peer lending, activity logging, real-time synchronization, and dashboard analytics.

---

## 📌 Features

### Authentication & User Isolation
* **User Registration & Login:** Email and password authentication with complexity validation (8–72 characters, uppercase, lowercase, digit, and special symbol).
* **JWT Access Tokens:** Short-lived (15-minute) signed JWT tokens held strictly in React application memory—never persisted in `localStorage` or `sessionStorage`.
* **HttpOnly Refresh Cookies:** Long-lived (7-day) cryptographically random refresh tokens stored in secure, `HttpOnly`, `SameSite=Lax` cookies, protected from cross-site scripting (XSS).
* **Token Rotation & Pessimistic Concurrency:** Single-use refresh token rotation guarded by PostgreSQL row-level locks (`SELECT ... FOR UPDATE`), preventing token replay and race conditions.
* **Revocation on Logout:** Instant server-side revocation on logout by deleting the stored token hash and clearing browser cookies.
* **Password Hashing:** Passwords hashed with `bcrypt` (enforcing the 72-byte truncation boundary prior to hashing).
* **Multi-User Isolation:** Strict database-level scoping ensuring users can only view, modify, or query their own catalog and authorized collaborations.

### Book Catalog Management
* **Full CRUD Lifecycle:** Add, view, edit (full PUT and partial PATCH), and delete books from personal collections.
* **Server-Side Pagination:** PostgreSQL `LIMIT` and `OFFSET` execution with total record counting and page calculation.
* **Live Search:** Fast, case-insensitive keyword search against both book title and author using SQL `ILIKE`.
* **Status Filtering:** Filter library catalog by reading state (`want_to_read`, `reading`, `finished`).
* **Multi-Criteria Sorting:** Sort by date added, updated date, title, author, rating, or current page, with deterministic secondary sorting by `id ASC` to prevent pagination jitter.
* **Reading Progress:** Real-time page count tracking with computed percentage and input boundary checks (`current_page <= total_pages`).
* **Automatic Status Lifecycle:** State machine automatically advances `want_to_read` to `reading` on progress, marks books `finished` when reaching the final page, and sets/clears completion dates.

### Custom Shelves & Role-Based Access Control (RBAC)
* **Custom Shelves:** Create, list, rename, and delete custom shelves (enforced unique shelf names per user).
* **Many-to-Many Relationships:** Flexible categorization allowing books to belong to multiple shelves simultaneously via `shelf_books`.
* **Shelf Sharing & RBAC:** Three granular privilege tiers:
  * **Owner:** Full control—create, rename, delete shelf, invite/remove collaborators, change roles, and add/remove own books.
  * **Editor:** Add and remove their own books to/from the shared shelf; cannot rename/delete the shelf or manage collaborators.
  * **Viewer:** Read-only access—view shelf metadata, assigned books, and member lists.
* **Backend-Enforced Authorization:** Centralized permission resolver (`get_shelf_with_role`) guarantees security rules are enforced at the API layer, returning `404 Not Found` for uninvited users to prevent leaking private shelf existence.
* **Member Book Ownership Isolation:** Collaborators can only assign books they personally own to shared shelves; member books remain safely in the creator's library if a shelf is removed.

### Reading Progress Tracking & Milestones
* **Dedicated Progress Endpoint:** Dedicated `POST /api/books/{id}/progress` endpoint supporting page updates, reflection notes, and star ratings.
* **Percentage & Boundary Validation:** Strict validation ensures current page cannot be negative or exceed total page count.
* **Milestone Detection:** Single-trigger milestone detection at 25% (quarter), 50% (half), 75% (three-quarters), and 100% (completed).
* **Automatic Finish:** Setting `current_page == total_pages` automatically marks the book as `finished` and records the UTC completion timestamp.
* **Audit Trail Generation:** Atomic creation of at most one audit record per update (prioritizing `status_changed` over `progress_updated`).

### Peer-to-Peer Book Lending
* **Registered-User Lending:** Lend physical copies of owned books to other registered users by email address.
* **Active-Loan Protection:** Invariant enforced at the database engine level via PostgreSQL partial unique index `ix_lending_active_book` (`book_id WHERE is_active = true`), guaranteeing a book cannot be lent simultaneously to multiple borrowers.
* **Owner-Only Return Action:** Only the book owner/lender can mark an active loan as returned (`POST /api/lending/{id}/return`).
* **Borrower Read-Only View:** Dedicated `/api/lending/borrowed` endpoint allows borrowers to see lent book details without modifying the owner's library record.
* **Lending History:** Owners maintain a complete chronological record of all historical and active loans for every book in their catalog.

### Activity Feed & Audit Logging
* **Audited System Events:** Comprehensive logging across `book_added`, `status_changed`, `progress_updated`, `shelf_shared`, `shelf_role_changed`, `shelf_share_removed`, `book_lent`, and `book_returned`.
* **Reverse Chronological Feed:** Server-side paginated activity feed ordered newest-first.
* **Privacy & Visibility Scoping:** Personal catalog activities are isolated to the owner; shelf activities are visible only to active collaborators; lending activities are restricted to the lender and borrower.

### Real-Time Synchronization (WebSockets)
* **Socket.IO Integration:** Bi-directional event broadcasting powered by `python-socketio` mounted directly on the ASGI application.
* **Authenticated Handshake:** WebSocket connection handshake verifies short-lived JWT access tokens; unauthenticated connections or refresh tokens are rejected.
* **Personal & Shelf Rooms:** Clients join personal rooms (`user_{user_id}`) for private notifications and shelf rooms (`shelf_{shelf_id}`) for shared collaboration.
* **Instant Room Revocation:** When an owner revokes collaborator access, the collaborator's active socket connections are evicted from the shelf room immediately and sent a revocation notice.
* **Post-Commit Event Broadcast:** Real-time events are dispatched only after the database transaction successfully commits.
* **Lightweight Refetch Pattern:** React frontend hooks respond to WebSocket events by refetching only affected data queries, preserving server-side pagination, sorting, and search state without race conditions.

### Analytics Dashboard
* **Server-Side Aggregations:** Consolidated dashboard summary endpoint (`GET /api/dashboard/summary`) calculated via SQL aggregations:
  * Reading status counts (`want_to_read`, `reading`, `finished`).
  * Books finished within the current calendar year.
  * Average rating of owned rated books.
  * Top shelf owned with the most books (with deterministic tie-breaking).
  * Count of owned books currently lent out.
  * Count of shelves shared with the user by others.
* **Recent Activity Stream:** Instant feed of the user's latest actions integrated directly into the dashboard view.

---

## ⚡ Tech Stack

### Backend
* **Language & Runtime:** Python 3.11+
* **Web Framework:** FastAPI 0.115.0
* **ASGI Server:** Uvicorn 0.30.0
* **Database ORM:** SQLAlchemy 2.0.35
* **Database Driver:** Psycopg 3.2.3 (`psycopg[binary]`)
* **Database Engine:** PostgreSQL 15+
* **Migrations:** Alembic 1.13.0
* **Data Validation:** Pydantic 2.9.0 & Pydantic Settings 2.5.0
* **Authentication & JWT:** `python-jose[cryptography]` 3.3.0
* **Password Hashing:** `passlib[bcrypt]` 1.7.4 & `bcrypt` 4.0.1
* **Real-time WebSockets:** `python-socketio` 5.11.0 (ASGI mode)
* **Testing & HTTP Client:** `httpx` 0.28.1

### Frontend
* **UI Framework:** React 19.3.0
* **Build Tool & Dev Server:** Vite 8.3.0
* **Routing:** React Router 7.18.4 (`react-router-dom`)
* **HTTP Client:** Axios 1.20.0 (configured with interceptors, replay queue, and `withCredentials: true`)
* **WebSocket Client:** `socket.io-client` 4.8.3
* **Typography & Styling:** Vanilla CSS with CSS custom properties (design tokens) and Google Fonts (Inter)

### Infrastructure & Tooling
* **Version Control:** Git
* **Integration Testing:** Executable Python asynchronous test suites (`httpx` + `python-socketio`)

---

## 💡 Why This Stack / Architecture

BookNest is built as a decoupled, high-integrity client-server application:

* **React + Vite:** Vite provides instant dev server start, sub-second Hot Module Replacement (HMR), and clean asset bundling. Building the frontend as a pure client Single Page Application (SPA) avoids Server-Side Rendering (SSR) hydration complexity and keeps the long-lived WebSocket connection stable across page transitions.
* **FastAPI:** Provides high-performance asynchronous HTTP handling, Python type hints, Pydantic request/response schema validation, dependency injection for session management, and auto-generated OpenAPI documentation.
* **PostgreSQL:** Provides strict transactional relational storage (ACID), foreign keys with cascading deletions, check constraints, and PostgreSQL-specific partial unique indexes that enforce business invariants directly in the database engine.
* **SQLAlchemy 2.0:** Enables type-annotated query construction, relationships, and selective join loading (`selectinload`), avoiding N+1 query overhead.
* **Alembic:** Provides declarative, repeatable schema versioning and database migration tracking.
* **Python-SocketIO:** Provides low-latency event broadcasting with room abstractions (`user_{id}`, `shelf_{id}`) running directly within the ASGI application lifecycle.

### High-Level Architecture Flow

```
[ Frontend: React 19 SPA ]
      │             ▲
  HTTP REST     WebSocket
(Axios + JWT)  (Socket.IO)
      │             ▲
      ▼             │
[ ASGI Application Wrapper: socket_app (Port 8000) ]
      ├──> FastAPI Router Layer (/api/auth, /books, /shelves, /lending, /dashboard)
      │         │
      │    Service Layer (auth_service, book_service, shelf_service, lending_service)
      │         │
      │    SQLAlchemy 2.0 ORM
      │         │
      │    PostgreSQL Database (Tables, Checks, Partial Unique Index)
      │
      └──> Python-SocketIO Server (ASGI)
                │
           Realtime Broadcasts (Personal & Shelf Rooms)
```

---

## 📂 Project Structure

```
BookNest/
├── backend/
│   ├── alembic/
│   │   ├── versions/
│   │   │   └── 2026_09_17_1857-19f40499af4c_initial_tables.py   # Complete schema migration
│   │   ├── env.py                                               # Alembic runtime environment
│   │   └── script.py.mako
│   ├── app/
│   │   ├── models/                                              # SQLAlchemy 2.0 ORM models
│   │   │   ├── __init__.py                                      # Metadata registry
│   │   │   ├── activity_log.py                                  # ActivityLog entity
│   │   │   ├── book.py                                          # Book entity with check constraints
│   │   │   ├── lending.py                                       # Lending entity with partial index
│   │   │   ├── refresh_token.py                                 # RefreshToken entity (SHA-256 hashes)
│   │   │   ├── shelf.py                                         # Shelf entity
│   │   │   ├── shelf_book.py                                    # ShelfBook (many-to-many join)
│   │   │   ├── shelf_share.py                                   # ShelfShare (collaborator RBAC)
│   │   │   └── user.py                                          # User entity
│   │   ├── schemas/                                             # Pydantic validation schemas
│   │   │   ├── activity.py
│   │   │   ├── auth.py
│   │   │   ├── book.py
│   │   │   ├── dashboard.py
│   │   │   ├── lending.py
│   │   │   └── shelf.py
│   │   ├── services/                                            # Domain business logic & invariants
│   │   │   ├── activity_service.py                              # Activity feed and audit logging
│   │   │   ├── auth_service.py                                  # JWT issuance & pessimistic rotation
│   │   │   ├── book_service.py                                  # Catalog CRUD, pagination, milestones
│   │   │   ├── dashboard_service.py                             # Server-side SQL dashboard metrics
│   │   │   ├── lending_service.py                               # Peer lending & return operations
│   │   │   ├── realtime_service.py                              # Socket.IO rooms & event dispatch
│   │   │   └── shelf_service.py                                 # Shelf operations & RBAC resolver
│   │   ├── routers/                                             # FastAPI HTTP endpoints
│   │   │   ├── activity.py                                      # /api/activities
│   │   │   ├── auth.py                                          # /api/auth
│   │   │   ├── books.py                                         # /api/books
│   │   │   ├── dashboard.py                                     # /api/dashboard
│   │   │   ├── lending.py                                       # /api/lending
│   │   │   └── shelves.py                                       # /api/shelves
│   │   ├── config.py                                            # Typed settings (pydantic-settings)
│   │   ├── database.py                                          # SQLAlchemy engine & session factory
│   │   ├── dependencies.py                                      # get_current_user & get_db injection
│   │   └── main.py                                              # FastAPI app & Socket.IO ASGI mount
│   ├── alembic.ini                                              # Migration configuration
│   ├── requirements.txt                                         # Python package dependencies
│   ├── seed.py                                                  # Deterministic, idempotent demo seed
│   ├── test_auth_phase2.py                                      # Auth integration test suite
│   ├── test_books_phase3.py                                     # Books CRUD test suite
│   ├── test_pagination.py                                       # Server-side pagination test suite
│   ├── test_shelves_phase4.py                                   # Shelves & M:N test suite
│   ├── test_shelf_sharing_phase5.py                             # Shelf sharing & RBAC test suite
│   ├── test_progress_phase6.py                                  # Reading progress & milestones test
│   ├── test_lending_phase7.py                                   # Peer lending & return test suite
│   ├── test_activity_phase8.py                                  # Activity logging & scoping test suite
│   ├── test_realtime_phase9.py                                  # WebSocket Socket.IO test suite
│   ├── test_dashboard_step2.py                                  # Dashboard metrics test suite
│   ├── test_seed.py                                             # Seed script verification test suite
│   └── .env.example                                             # Backend environment template
├── frontend/
│   ├── public/                                                  # Static assets & favicon
│   ├── src/
│   │   ├── api/                                                 # Axios API clients
│   │   │   ├── activity.js
│   │   │   ├── auth.js
│   │   │   ├── books.js
│   │   │   ├── client.js                                        # Axios instance with 401 replay queue
│   │   │   ├── dashboard.js
│   │   │   ├── lending.js
│   │   │   └── shelves.js
│   │   ├── components/                                          # Modular React components
│   │   │   ├── ActivityFeed.jsx
│   │   │   ├── AssignShelfModal.jsx
│   │   │   ├── BookCard.jsx
│   │   │   ├── BookModal.jsx
│   │   │   ├── DashboardSummary.jsx
│   │   │   ├── LendBookModal.jsx
│   │   │   ├── LendingHistoryModal.jsx
│   │   │   ├── Navbar.jsx
│   │   │   ├── ProgressModal.jsx
│   │   │   ├── ProtectedRoute.jsx
│   │   │   ├── ReadingStatsBanner.jsx
│   │   │   ├── ShelfModal.jsx
│   │   │   ├── ShelfShareModal.jsx
│   │   │   └── ShelfSidebar.jsx
│   │   ├── context/                                             # Global React contexts
│   │   │   ├── AuthContext.jsx                                  # User state & session initialization
│   │   │   └── SocketContext.jsx                                # Socket.IO connection & rooms
│   │   ├── hooks/                                               # Custom React hooks
│   │   │   ├── useApi.js
│   │   │   └── useSocket.js
│   │   ├── pages/                                               # Application views
│   │   │   ├── Dashboard.jsx                                    # Main app interface
│   │   │   ├── Login.jsx                                        # User sign-in
│   │   │   └── Signup.jsx                                       # User registration
│   │   ├── styles/
│   │   │   ├── global.css                                       # CSS resets & utility styles
│   │   │   └── variables.css                                    # Theme tokens & variables
│   │   ├── App.jsx                                              # Root component & route config
│   │   └── main.jsx                                             # React DOM entrypoint
│   ├── index.html                                               # Entry HTML with Inter font loader
│   ├── package.json                                             # Frontend dependencies and scripts
│   ├── tsconfig.json                                            # TypeScript/bundler configuration
│   └── vite.config.js                                           # Vite dev proxy configuration
├── tests/
│   └── conftest.py
├── .env.example                                                 # Root environment template
├── .gitignore
└── README.md
```

---

## 🗄️ Data Model

The application uses 8 relational tables managed via Alembic migration `19f40499af4c`:

```
┌──────────────┐       1:N       ┌──────────────────┐
│    users     ├────────────────>│      books       │
└──────┬───────┘                 └────────┬─────────┘
       │                                  │
       │ 1:N                              │ 1:N
       ▼                                  ▼
┌──────────────┐       1:N       ┌──────────────────┐
│   shelves    ├────────────────>│   shelf_books    │ (M:N Join)
└──────┬───────┘                 └──────────────────┘
       │
       │ 1:N
       ▼
┌──────────────┐
│ shelf_shares │ (RBAC: editor / viewer)
└──────────────┘

┌──────────────┐                 ┌──────────────────┐
│   lendings   │                 │  activity_logs   │
│ (Partial Idx)│                 └──────────────────┘
└──────────────┘
┌──────────────┐
│refresh_tokens│
│(Hashed Store)│
└──────────────┘
```

### Table Definitions & Constraints

1. **`users`**:
   * Fields: `id` (UUID PK), `name` (VARCHAR), `email` (VARCHAR, Unique, Indexed), `password_hash` (VARCHAR), `created_at` (TIMESTAMPTZ).
   * Relationships: Owns books, shelves, activity logs, refresh tokens, and lending transactions.
2. **`books`**:
   * Fields: `id` (UUID PK), `user_id` (UUID FK -> `users.id` CASCADE), `title` (VARCHAR), `author` (VARCHAR), `status` (VARCHAR, Indexed), `total_pages` (INT NULL), `current_page` (INT), `rating` (INT NULL), `notes` (TEXT NULL), `finished_date` (TIMESTAMPTZ NULL), `created_at` (TIMESTAMPTZ, Indexed), `updated_at` (TIMESTAMPTZ).
   * Check Constraints:
     * `ck_book_status`: `status IN ('want_to_read', 'reading', 'finished')`
     * `ck_book_rating`: `rating >= 1 AND rating <= 5`
     * `ck_book_current_page`: `current_page >= 0`
3. **`shelves`**:
   * Fields: `id` (UUID PK), `user_id` (UUID FK -> `users.id` CASCADE), `name` (VARCHAR), `created_at` (TIMESTAMPTZ).
   * Constraints: `uq_shelf_user_name` Unique constraint on `(user_id, name)`.
4. **`shelf_books`**:
   * Join table implementing the many-to-many relationship between shelves and books.
   * Fields: `id` (UUID PK), `shelf_id` (UUID FK -> `shelves.id` CASCADE), `book_id` (UUID FK -> `books.id` CASCADE), `added_at` (TIMESTAMPTZ).
   * Constraints: `uq_shelf_book` Unique constraint on `(shelf_id, book_id)` preventing duplicate shelf assignments.
5. **`shelf_shares`**:
   * Role-based collaborator relationship on shared shelves.
   * Fields: `id` (UUID PK), `shelf_id` (UUID FK -> `shelves.id` CASCADE), `user_id` (UUID FK -> `users.id` CASCADE), `role` (VARCHAR), `created_at` (TIMESTAMPTZ).
   * Constraints: `uq_shelf_share_user` Unique constraint on `(shelf_id, user_id)` preventing duplicate shares to the same user; `ck_shelf_share_role` Check constraint `role IN ('editor', 'viewer')`.
6. **`lendings`**:
   * Peer-to-peer loan tracking records.
   * Fields: `id` (UUID PK), `book_id` (UUID FK -> `books.id` CASCADE), `lender_id` (UUID FK -> `users.id` CASCADE), `borrower_id` (UUID FK -> `users.id` CASCADE), `is_active` (BOOLEAN, Indexed), `lent_at` (TIMESTAMPTZ), `returned_at` (TIMESTAMPTZ NULL).
   * **Partial Unique Index:** `ix_lending_active_book` on `book_id WHERE is_active = true`. Enforces at the database engine level that no book can have more than one active loan simultaneously.
7. **`activity_logs`**:
   * Append-only audit logging table.
   * Fields: `id` (UUID PK), `user_id` (UUID FK -> `users.id` CASCADE), `action` (VARCHAR, Indexed), `details` (JSON NULL), `shelf_id` (UUID FK -> `shelves.id` SET NULL), `created_at` (TIMESTAMPTZ, Indexed).
8. **`refresh_tokens`**:
   * Storage for hashed refresh tokens.
   * Fields: `id` (UUID PK), `user_id` (UUID FK -> `users.id` CASCADE), `token_hash` (VARCHAR, Unique, Indexed), `expires_at` (TIMESTAMPTZ, Indexed), `created_at` (TIMESTAMPTZ).

---

## 🔐 Authentication & Refresh Flow

BookNest uses a defense-in-depth token authentication architecture:

```
[ User Action: Login / Signup ]
              │
              ▼
   POST /api/auth/login
              │
   ┌──────────┴────────────────────────┐
   ▼                                   ▼
Response Body:                    Set-Cookie:
{ access_token }             refresh_token=<raw_token>
(Stored in React memory)     (HttpOnly, SameSite=Lax, Path=/api/auth)
                                       │
                                       ▼
                             PostgreSQL Database:
                             Stores SHA-256(raw_token)
```

### Access & Refresh Lifecycle
1. **Token Lifetimes:**
   * **Access Token:** 15 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES=15`).
   * **Refresh Token:** 7 days (`REFRESH_TOKEN_EXPIRE_DAYS=7`).
2. **Cookie Security:**
   * The refresh token cookie is configured with `HttpOnly=True`, `SameSite=Lax`, and `Path=/api/auth`.
   * `Secure`: Controlled dynamically via the `COOKIE_SECURE` environment variable (`false` in local development over HTTP; `true` in HTTPS production).
3. **Database Hash Storage:**
   * Raw refresh tokens are never written to disk. Only deterministic SHA-256 hex digests (`token_hash`) are stored in PostgreSQL.
4. **Pessimistic Rotation Concurrency (`SELECT ... FOR UPDATE`):**
   * Single-use rotation: When a client calls `/api/auth/refresh`, the server looks up the token record using a pessimistic row-level lock (`with_for_update()`).
   * If two requests with the same refresh token arrive simultaneously, the first acquires the lock, invalidates the old record, and issues new tokens. The second request unblocks, discovers the token row no longer exists, and is rejected with `401 Unauthorized`.
5. **Revocation:**
   * Calling `POST /api/auth/logout` deletes the hashed token row from PostgreSQL and instructs the browser to clear the cookie.
6. **Frontend Silent Refresh & Replay Queue:**
   * In [`frontend/src/api/client.js`](frontend/src/api/client.js), an Axios response interceptor intercepts `401 Unauthorized` errors.
   * If a refresh is already in progress, subsequent failing requests are placed into a promise queue (`failedQueue`).
   * The interceptor calls `POST /api/auth/refresh`. Upon success, the new access token is stored in memory, all queued requests are replayed with the new Bearer header, and the original request is executed.
   * Anti-loop safeguards prevent recursion on authentication endpoints (`/auth/login`, `/auth/signup`, `/auth/refresh`). If refresh fails, memory state is wiped and the user is redirected to `/login`.

---

## 🛡️ Backend Role-Based Access Control (RBAC)

Shelf collaboration permissions are strictly enforced on the backend via the centralized `get_shelf_with_role(db, user_id, shelf_id)` service function.

| Action | Shelf Owner | Editor | Viewer | Unauthorized User |
|---|:---:|:---:|:---:|:---:|
| **View shelf metadata & books** | ✅ Allowed | ✅ Allowed | ✅ Allowed | ❌ 404 Not Found |
| **View collaborator list** | ✅ Allowed | ✅ Allowed | ✅ Allowed | ❌ 404 Not Found |
| **Add owned book to shelf** | ✅ Allowed | ✅ Allowed | ❌ 403 Forbidden | ❌ 404 Not Found |
| **Remove book from shelf** | ✅ Allowed | ✅ Allowed | ❌ 403 Forbidden | ❌ 404 Not Found |
| **Rename shelf** | ✅ Allowed | ❌ 403 Forbidden | ❌ 403 Forbidden | ❌ 404 Not Found |
| **Delete shelf** | ✅ Allowed | ❌ 403 Forbidden | ❌ 403 Forbidden | ❌ 404 Not Found |
| **Invite collaborator** | ✅ Allowed | ❌ 403 Forbidden | ❌ 403 Forbidden | ❌ 404 Not Found |
| **Change collaborator role** | ✅ Allowed | ❌ 403 Forbidden | ❌ 403 Forbidden | ❌ 404 Not Found |
| **Remove collaborator** | ✅ Allowed | ❌ 403 (Can leave) | ❌ 403 (Can leave) | ❌ 404 Not Found |

### Key Authorization Principles
* **Information Leakage Prevention:** Unauthorized users requesting an unshared shelf receive `404 Not Found` rather than `403 Forbidden`, preventing enumeration of private user collections.
* **Book Ownership Invariant:** An editor adding a book to a shared shelf can only add a book they personally own (`Book.user_id == current_user.id`).
* **Cascade Isolation:** Deleting a shared shelf deletes only the shelf and join rows (`shelf_books`, `shelf_shares`); all actual books remain intact in their respective owners' libraries.

---

## 📄 Server-Side Book Pagination, Search & Sorting

Book catalog listing (`GET /api/books`) executes entirely within the database engine rather than loading records into memory:

* **Query Parameters:**
  * `page` (default: 1)
  * `page_size` (default: 10, max: 100)
  * `status` (optional: `want_to_read`, `reading`, `finished`)
  * `shelf_id` (optional: UUID of shelf)
  * `search` (optional: search term)
  * `sort_by` (optional: `created_at`, `date_added`, `updated_at`, `title`, `author`, `rating`, `current_page`)
  * `sort_dir` (optional: `asc`, `desc`)
* **SQL Filtering & Search:**
  * Status filtering: `WHERE books.status = :status`
  * Text search: `WHERE (books.title ILIKE :term OR books.author ILIKE :term)`
  * Shelf scoping: Joins `shelf_books` after checking RBAC access.
* **Database Aggregation & Pagination:**
  * Exact matching count computed via `SELECT COUNT(*) ...` prior to pagination.
  * Sliced at SQL level using `.offset((page - 1) * page_size).limit(page_size)`.
* **Deterministic Stable Secondary Sorting:**
  * Sorting always appends `Book.id.asc()` as a secondary sort criterion (e.g. `ORDER BY rating DESC NULLS LAST, id ASC`). This guarantees that pagination boundaries remain stable when multiple books share identical ratings, titles, or dates.
* **Response Payload (`PaginatedBooksResponse`):**
  ```json
  {
    "items": [...],
    "total": 42,
    "page": 1,
    "page_size": 10,
    "total_pages": 5
  }
  ```

---

## ⚡ WebSocket & Real-Time Design

Real-time collaboration is built with `python-socketio` mounted as an ASGI application wrapper alongside FastAPI in [`backend/app/main.py`](backend/app/main.py):

```python
socket_app = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=app,
    socketio_path="socket.io",
)
```

### Handshake Authentication
* Clients authenticate during the Socket.IO connection handshake by passing the short-lived JWT access token in the `auth` object (`{ auth: { token: accessToken } }`).
* Handshake validation decodes the token with the server's `SECRET_KEY`, validates expiration, and strictly verifies `token_type == 'access'`. Refresh tokens or unauthenticated attempts are rejected.

### Room Architecture & Scoping
* **Personal Room (`user_{user_id}`):** Automatically joined upon connection. Delivers private events such as book additions, progress updates, lending notifications, and revocation alerts.
* **Shelf Room (`shelf_{shelf_id}`):** Clients join via `sio.emit("join_shelf", { shelf_id })`. The server queries the database to verify the user is an owner, editor, or viewer before granting room entry.
* **Instantaneous Access Revocation:** When a shelf owner removes a collaborator, the server calls `remove_user_from_shelf_room()`, iterating over the user's active session IDs, removing them from `shelf_{shelf_id}`, and emitting `shelf_access_revoked` to their personal room.

### Post-Commit Event Emission
Real-time events are dispatched only after the active database transaction has committed:
* `book_added`, `book_updated`, `book_deleted`
* `progress_updated`
* `shelf_created`, `shelf_renamed`, `shelf_deleted`
* `shelf_book_added`, `shelf_book_removed`
* `shelf_shared`, `shelf_role_changed`, `shelf_share_removed`
* `book_lent`, `book_returned`
* `activity_created`

### Lightweight Refetch Synchronization
The React frontend avoids brittle client-side cache manipulation. When a real-time event is received, `useSocket` triggers lightweight refetch callbacks (`fetchBooks`, `fetchShelves`, `fetchDashboardSummary`, `fetchActivities`), preserving server-side pagination offsets, active search queries, and status filters.

---

## 🌐 API Overview

All REST routes are prefixed with `/api`. Interactive documentation is available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

### System & Health
| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `GET` | `/api/health` | Health check endpoint (`{"status": "ok"}`) | Public |

### Authentication (`/api/auth`)
| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `POST` | `/api/auth/signup` | Register new user; returns access token + set HttpOnly cookie | Public |
| `POST` | `/api/auth/login` | Authenticate user; returns access token + set HttpOnly cookie | Public |
| `POST` | `/api/auth/refresh` | Rotate refresh token via HttpOnly cookie; returns new access token | Cookie |
| `POST` | `/api/auth/logout` | Revoke active refresh token in database and delete cookie | Public |
| `GET` | `/api/auth/me` | Retrieve authenticated user profile | Bearer |

### Books Catalog (`/api/books`)
| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `GET` | `/api/books` | Server-side paginated, searchable, status-filtered book list | Bearer |
| `POST` | `/api/books` | Add new book to personal library | Bearer |
| `GET` | `/api/books/stats/summary` | Aggregated user reading statistics | Bearer |
| `GET` | `/api/books/{id}` | Get book detail (owner only) | Bearer |
| `PATCH` | `/api/books/{id}` | Partial book update with boundary validation | Bearer |
| `PUT` | `/api/books/{id}` | Full book update | Bearer |
| `DELETE` | `/api/books/{id}` | Delete book from library (owner only) | Bearer |
| `POST` | `/api/books/{id}/progress` | Record reading progress, detect milestones, auto-advance status | Bearer |

### Custom Shelves (`/api/shelves`)
| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `GET` | `/api/shelves` | List user's owned and shared custom shelves with book counts | Bearer |
| `POST` | `/api/shelves` | Create custom shelf (enforces unique name per user) | Bearer |
| `GET` | `/api/shelves/{id}` | Get shelf detail with books and collaborators (Owner/Editor/Viewer) | Bearer |
| `PATCH` | `/api/shelves/{id}` | Rename shelf (Owner only) | Bearer |
| `PUT` | `/api/shelves/{id}` | Update shelf (Owner only) | Bearer |
| `DELETE` | `/api/shelves/{id}` | Delete shelf (Owner only; cascade-safe, preserves books) | Bearer |
| `POST` | `/api/shelves/{id}/books` | Add owned book to shelf (Owner or Editor) | Bearer |
| `DELETE` | `/api/shelves/{id}/books/{book_id}` | Remove book from shelf (Owner or Editor) | Bearer |

### Shelf Collaboration & RBAC (`/api/shelves/{id}/shares`)
| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `POST` | `/api/shelves/{id}/shares` | Invite collaborator by email as `editor` or `viewer` (Owner only) | Bearer |
| `GET` | `/api/shelves/{id}/shares` | List active shelf collaborators (Owner/Editor/Viewer) | Bearer |
| `PATCH` | `/api/shelves/{id}/shares/{share_id}` | Update collaborator role (Owner only) | Bearer |
| `DELETE` | `/api/shelves/{id}/shares/{share_id}` | Remove collaborator (Owner) or leave shelf (Collaborator) | Bearer |

### Peer-to-Peer Book Lending (`/api/lending`)
| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `POST` | `/api/lending` | Lend owned book to registered user (Owner only; 409 if actively lent) | Bearer |
| `GET` | `/api/lending` | List loans with `role` (`lender`/`borrower`/`all`) and `status` filters | Bearer |
| `GET` | `/api/lending/borrowed` | List active books borrowed by authenticated user (read-only) | Bearer |
| `GET` | `/api/lending/borrowed/{book_id}` | Get read-only detail of single borrowed book | Bearer |
| `GET` | `/api/lending/book/{book_id}` | Complete lending history for owned book (Owner only) | Bearer |
| `POST` | `/api/lending/{id}/return` | Mark active loan returned (Owner/Lender only) | Bearer |
| `GET` | `/api/lending/{id}` | Get single loan record (Lender or Borrower only) | Bearer |

### Activity Feed (`/api/activities`)
| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `GET` | `/api/activities` | Server-side paginated activity feed with action and shelf filtering | Bearer |

### Dashboard Analytics (`/api/dashboard`)
| Method | Endpoint | Description | Auth |
|---|---|---|:---:|
| `GET` | `/api/dashboard/summary` | Aggregated dashboard summary metrics calculated via SQL | Bearer |

### WebSockets (`/socket.io/`)
| Protocol | Path | Description | Handshake Auth |
|---|---|---|:---:|
| `WS` | `/socket.io/` | Bi-directional real-time event channel | JWT Access Token |

---

## 🚀 Setup & Running Locally

### Prerequisites
* **Python 3.11+**
* **Node.js 18+** and **npm**
* **PostgreSQL 15+** running locally
* **Git**

---

### 1. Database Setup

Create the PostgreSQL database using `psql` or your database management tool:

```sql
CREATE DATABASE booknest;
```

---

### 2. Backend Setup

1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   * **Windows (PowerShell):**
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```
   * **macOS / Linux:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. Install backend dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create your local `.env` configuration file from the template:
   * **Windows (PowerShell):**
     ```powershell
     Copy-Item .env.example .env
     ```
   * **macOS / Linux:**
     ```bash
     cp .env.example .env
     ```

5. Edit `backend/.env` with your PostgreSQL database credentials (e.g. `DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/booknest`).

6. Execute database migrations:
   ```bash
   alembic upgrade head
   ```

7. Start the backend ASGI server (serving both FastAPI and Socket.IO):
   ```bash
   uvicorn app.main:socket_app --reload --port 8000
   ```

The backend API and WebSocket server will run at **`http://localhost:8000`**.

---

### 3. Frontend Setup

1. Open a second terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install frontend dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

The frontend application will run at **`http://localhost:5173`**.

---

### Expected URLs
* **Frontend Application:** `http://localhost:5173`
* **Backend API & WebSockets:** `http://localhost:8000`
* **Interactive API Documentation (Swagger UI):** `http://localhost:8000/docs`
* **Alternative API Documentation (ReDoc):** `http://localhost:8000/redoc`
* **Backend Health Check:** `http://localhost:8000/api/health`

---

## ⚙️ Environment Variables

Create `.env` inside `backend/` using `backend/.env.example` as a template:

| Variable | Description | Default in `.env.example` |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/booknest` |
| `SECRET_KEY` | Secret key used to sign JWT access tokens | `your-secret-key-change-in-production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Lifespan of JWT access token in minutes | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Lifespan of refresh token in days | `7` |
| `CORS_ORIGINS` | JSON array of permitted CORS origins | `["http://localhost:5173"]` |
| `COOKIE_SECURE` | Set `false` for local HTTP; `true` for production HTTPS | `false` |

> **Note:** If your PostgreSQL password contains special characters (e.g., `@`), URL-encode them in `DATABASE_URL` (`@` becomes `%40`).

---

## 🧪 Demo Data

A deterministic, idempotent seed script is provided to populate realistic demo data across all application features.

### Running the Seed Script

Ensure your database is created and migrations are applied, then run:

* **Windows (PowerShell):**
  ```powershell
  cd backend
  .\venv\Scripts\python seed.py
  ```
* **macOS / Linux:**
  ```bash
  cd backend
  python seed.py
  ```

### Demo Accounts (Local Assessment Only)

| Role | Email | Password |
|---|---|---|
| **Demo Owner** | `owner@booknest.demo` | `DemoPassword123!` |
| **Demo Collaborator** | `collaborator@booknest.demo` | `DemoPassword123!` |

### What the Seed Script Demonstrates
* **7 Sample Books:**
  * *Clean Architecture* (Owner: finished, 352/352 pages, rating: 5)
  * *Designing Data-Intensive Applications* (Owner: reading, 280/616 pages, rating: 5)
  * *The Pragmatic Programmer* (Owner: want_to_read, 0/352 pages, rating: unrated)
  * *Domain-Driven Design* (Owner: reading, 150/560 pages, rating: 4, actively lent)
  * *Site Reliability Engineering* (Owner: finished, 550/550 pages, rating: 4)
  * *Refactoring* (Collaborator: reading, 120/448 pages, rating: 5)
  * *Patterns of Enterprise Application Architecture* (Collaborator: want_to_read, 0/560 pages)
* **4 Custom Shelves:**
  * Owner: "Favorites" (3 books), "Currently Reading" (2 books), "Backend & Tech" (1 book)
  * Collaborator: "Collab Reading Circle" (1 book)
* **2 Collaborative Shelf Shares:**
  * "Favorites" shared with Demo Collaborator as **Editor**
  * "Backend & Tech" shared with Demo Collaborator as **Viewer**
* **1 Active Peer Loan:**
  * *Domain-Driven Design* actively lent from Demo Owner to Demo Collaborator (enforcing active loan protection and borrower read-only view)
* **Idempotent Audit Log Entries:**
  * Pre-seeded activity log records for book additions, shelf sharing, and lending events using deterministic `seed_tag` identifiers.
* **Idempotency Guarantee:**
  * Running `seed.py` multiple times reuses existing records without throwing duplicate key errors or modifying existing data.

---

## 🔬 Testing

The repository contains 11 dedicated, executable Python integration test suites that verify backend business logic, database invariants, and real-time WebSockets against the live running application.

### Running Backend Test Suites

Ensure the backend server is running in a terminal (`uvicorn app.main:socket_app --reload --port 8000`), then run the test suites from `backend/`:

```powershell
cd backend

# Phase 2: Authentication, Password Complexity, Token Rotation
.\venv\Scripts\python test_auth_phase2.py

# Phase 3: Book Management, Validation, Multi-User Isolation
.\venv\Scripts\python test_books_phase3.py

# Server-Side Pagination, Filtering, Search, Sorting
.\venv\Scripts\python test_pagination.py

# Phase 4: Custom Shelves, Many-to-Many Relationships, Cascade Safety
.\venv\Scripts\python test_shelves_phase4.py

# Phase 5: Shared Shelves, RBAC (Owner / Editor / Viewer)
.\venv\Scripts\python test_shelf_sharing_phase5.py

# Phase 6: Reading Progress, Milestone Triggers, Auto-Transitions
.\venv\Scripts\python test_progress_phase6.py

# Phase 7: Peer Lending, Partial Unique Index, Owner Return
.\venv\Scripts\python test_lending_phase7.py

# Phase 8: Activity Feed, Scoped Visibility, Audit Logging
.\venv\Scripts\python test_activity_phase8.py

# Phase 9: Real-time WebSockets, Handshake Auth, Room Eviction
.\venv\Scripts\python test_realtime_phase9.py

# Dashboard Summary SQL Aggregations
.\venv\Scripts\python test_dashboard_step2.py

# Demo Seed Script Idempotency & Invariants
.\venv\Scripts\python test_seed.py
```

*(On macOS/Linux, replace `.\venv\Scripts\python` with `python`).*

### Frontend Build Verification

To verify that the frontend compiles cleanly without TypeScript or bundling errors:

```bash
cd frontend
npm run build
```

---

## 📋 Assessment Requirement Coverage

| Assessment Requirement Area | Implementation Status | Key Architecture & Verification Files |
|---|:---:|---|
| **User Authentication** | ✅ Implemented | HttpOnly cookie refresh, bcrypt hashing, row-level rotation lock ([`backend/app/services/auth_service.py`](backend/app/services/auth_service.py), [`backend/test_auth_phase2.py`](backend/test_auth_phase2.py)) |
| **Book Management & CRUD** | ✅ Implemented | Multi-user isolation, check constraints, cross-field validation ([`backend/app/services/book_service.py`](backend/app/services/book_service.py), [`backend/test_books_phase3.py`](backend/test_books_phase3.py)) |
| **Server-Side Pagination & Search** | ✅ Implemented | SQL-level `LIMIT`/`OFFSET`, `ILIKE` search, stable secondary sorting ([`backend/app/services/book_service.py`](backend/app/services/book_service.py), [`backend/test_pagination.py`](backend/test_pagination.py)) |
| **Custom Shelves (M:N)** | ✅ Implemented | `ShelfBook` join table, unique shelf name constraint per user, cascade safety ([`backend/app/services/shelf_service.py`](backend/app/services/shelf_service.py), [`backend/test_shelves_phase4.py`](backend/test_shelves_phase4.py)) |
| **Collaborative Shelves & RBAC** | ✅ Implemented | Owner / Editor / Viewer tiers, backend-enforced permission resolver, owner book isolation ([`backend/app/services/shelf_service.py`](backend/app/services/shelf_service.py), [`backend/test_shelf_sharing_phase5.py`](backend/test_shelf_sharing_phase5.py)) |
| **Reading Progress & Lifecycle** | ✅ Implemented | Dedicated progress updates, automatic status transitions, single milestone triggers ([`backend/app/services/book_service.py`](backend/app/services/book_service.py), [`backend/test_progress_phase6.py`](backend/test_progress_phase6.py)) |
| **Peer-to-Peer Book Lending** | ✅ Implemented | PostgreSQL partial unique index `ix_lending_active_book`, owner-only return action, borrower read-only view ([`backend/app/services/lending_service.py`](backend/app/services/lending_service.py), [`backend/test_lending_phase7.py`](backend/test_lending_phase7.py)) |
| **Activity Feed & Audit Logging** | ✅ Implemented | Atomic activity creation, reverse-chronological feed, scoped multi-user visibility ([`backend/app/services/activity_service.py`](backend/app/services/activity_service.py), [`backend/test_activity_phase8.py`](backend/test_activity_phase8.py)) |
| **Real-Time Synchronization** | ✅ Implemented | `python-socketio` ASGI mount, access token handshake auth, personal/shelf rooms, instant collaborator eviction ([`backend/app/services/realtime_service.py`](backend/app/services/realtime_service.py), [`backend/test_realtime_phase9.py`](backend/test_realtime_phase9.py)) |
| **Analytics Dashboard** | ✅ Implemented | Server-side SQL aggregations (`GROUP BY`, `AVG`, `COUNT`), top shelf calculation with tie-breaking ([`backend/app/services/dashboard_service.py`](backend/app/services/dashboard_service.py), [`backend/test_dashboard_step2.py`](backend/test_dashboard_step2.py)) |
| **Demo Seed Script** | ✅ Implemented | Deterministic, idempotent demo data populating 2 users, 7 books, 4 shelves, 2 shares, 1 loan, and activities ([`backend/seed.py`](backend/seed.py), [`backend/test_seed.py`](backend/test_seed.py)) |

---

## 🧠 Engineering Decisions & Technical Challenges

1. **Refresh Token Concurrency & Race Conditions:**
   * *Problem:* In single-page applications, opening multiple tabs or triggering multiple concurrent API requests on page load could trigger simultaneous token refresh calls, causing race conditions where one request invalidates the token before the other completes.
   * *Solution:* We applied pessimistic row-level locking (`SELECT ... FOR UPDATE` via `with_for_update()`) in PostgreSQL. The first refresh request acquires the lock and replaces the token. Subsequent concurrent requests unblock, detect the token hash has been rotated, and receive `401 Unauthorized`. In the frontend, an Axios request queue buffers concurrent requests until the active refresh resolves, replaying all waiting requests with the newly minted access token.
2. **Preventing Double Lending at the Database Engine Level:**
   * *Problem:* Checking whether a book is currently lent in application code is susceptible to race conditions under concurrent requests.
   * *Solution:* We created a PostgreSQL partial unique index: `CREATE UNIQUE INDEX ix_lending_active_book ON lendings (book_id) WHERE is_active = true`. PostgreSQL rejects any concurrent insertion attempting to create a second active loan on the same book, throwing an `IntegrityError` that the service catches and translates into a `409 Conflict`.
3. **Information Leakage in Shared Shelves:**
   * *Problem:* Returning `403 Forbidden` when an unauthorized user accesses `/api/shelves/{id}` inadvertently reveals that a shelf with that ID exists.
   * *Solution:* The permission resolver returns `404 Not Found` for any shelf the user neither owns nor has an active share for, preserving complete confidentiality.
4. **Stable Server-Side Pagination Across Sorting Ties:**
   * *Problem:* Sorting books by non-unique fields (e.g., `rating` or `status`) produces non-deterministic ordering in PostgreSQL across paginated offsets, leading to duplicate or skipped books across pages.
   * *Solution:* The query builder appends a deterministic secondary sort criterion (`Book.id.asc()`) to all queries, guaranteeing stable pagination boundaries.
5. **Real-Time Security & Instant Room Eviction:**
   * *Problem:* Revoking a user's share on a shelf could leave their active WebSocket connected to the shelf room, allowing them to continue eavesdropping on real-time collaboration events.
   * *Solution:* The service layer maintains an in-memory mapping of active socket session IDs per user. When an owner removes a collaborator, `remove_user_from_shelf_room` evicts all active sockets for that user from the shelf room immediately and emits a `shelf_access_revoked` notice to the user's private room.
6. **SQL-Level Dashboard Aggregations:**
   * *Problem:* Computing dashboard statistics by loading books and shelves into Python memory consumes excessive memory and scales poorly as libraries grow.
   * *Solution:* Metrics in `dashboard_service.py` are executed directly in PostgreSQL using SQL aggregations (`func.count`, `func.avg`, `func.distinct`, and `HAVING`), computing all metrics in single-digit milliseconds.

---

## ⚠️ Known Limitations

Known limitations as of the submission version:
* **Single-Process WebSocket Architecture:** `python-socketio` is configured with in-memory session and room state. Scaling horizontally across multiple server processes or containers would require attaching a Redis message broker adapter (`AsyncRedisManager`).
* **Handshake-Only WebSocket Token Expiration:** Access tokens are validated during the initial Socket.IO connection handshake. A persistent socket connection remains active until disconnected; reconnection triggers a new handshake validation.
* **Direct Database Collaboration Notifications:** Shelf invitations and peer loans are registered directly between existing user accounts in the database; transactional outbound email delivery (e.g. SMTP or AWS SES) is not configured.

---

## 🔮 Future Improvements

Sensible future enhancements for production deployment:
* **Automated CI/CD Pipeline:** GitHub Actions workflow executing linting, migrations, and automated integration test suites on pull requests.
* **Distributed Socket.IO Message Bus:** Redis adapter integration for horizontal backend scaling across multi-instance clusters.
* **Optimistic UI Updates:** Client-side optimistic cache updates for instantaneous reading progress slider feedback.
* **Library Import / Export:** Support for exporting catalog data to CSV/JSON and importing from Goodreads or OpenLibrary.
* **Email Notification Delivery:** Transactional emails for shelf share invitations and loan return reminders.

---

## 🤖 AI Usage Disclosure

AI-assisted development was used extensively during the development of BookNest.

AI tools were used for:
- Requirements interpretation and implementation planning
- Architecture and database design exploration
- Code generation and implementation across backend and frontend features
- Debugging and refactoring
- Test generation and verification scripts
- Documentation and README drafting

The development process was iterative: requirements were provided to the AI tools, generated implementations were inspected and adjusted where necessary, and the resulting application was run and tested locally against PostgreSQL and live browser sessions.

The developer remained responsible for directing the implementation, validating behavior against the assessment requirements, running the application, reviewing test results, identifying issues, and making final decisions about what was included in the submitted repository.

No AI-generated behavior was treated as automatically correct; the final implementation was validated through automated tests, clean-clone verification, API checks, and browser-based testing.

---

## 📦 Submission & Git Notes

* **Repository Integrity:** Public GitHub repository with a clean, granular, chronological Git commit history demonstrating iterative development across all phases.
* **Environment Configuration:** Comprehensive `.env.example` templates provided in both project root and `backend/`.
* **Database Migrations:** Schema managed through Alembic (`2026_09_17_1857-19f40499af4c_initial_tables.py`).
* **Seeded Demo State:** Fully automated, idempotent seed script (`backend/seed.py`) with verification suite (`backend/test_seed.py`).
* **Clean-Clone Readiness:** Fully documented local run commands enabling evaluators to run the application from a clean clone.
