# BookNest

> A full-stack reading tracker application designed for personal library management, custom shelf organization, collaborative shelf sharing with role-based permissions, reading progress tracking, and peer-to-peer book lending.

---

## 📌 Project Overview

BookNest is an application built for managing books, tracking reading milestones, and sharing collections with other users. It emphasizes real-world database relationships, transactional integrity, and edge-case handling (such as preventing duplicate active book loans via partial unique database indexes).

### Current Implementation Status
* **Phase 0 (Architecture Blueprint):** Complete domain model design, API endpoint specifications, permission matrices, and implementation sequencing.
* **Phase 1 (Project Scaffold & Database Layer):** Complete backend application skeleton, SQLAlchemy 2.0 ORM models, Alembic migrations executed against PostgreSQL, Vite + React frontend configuration with Axios client and local proxy, and design tokens.
* **Phase 2 (Authentication Layer):** Complete JWT access tokens in React memory, HttpOnly refresh cookies, SHA-256 token hashing, SELECT FOR UPDATE rotation concurrency safety, password policy enforcement, Axios 401 interceptor replay queue, and React Router protected routing.
* **Phase 3 (Book Management & Personal Library CRUD):** Complete personal book cataloging, Pydantic v2 cross-field validation, computed progress_percentage, status lifecycle management, strict multi-user isolation, and interactive library UI with search, status filters, and progress tracking.
* **Phase 4 (Custom Shelves & Many-to-Many Book Categorization):** Complete user-owned custom shelves, many-to-many book-to-shelf categorization, cascade safety, duplicate constraint race protection (409 Conflict), empty shelf listings via LEFT OUTER JOIN, dual-ownership shelf filtering, and responsive modular frontend (ShelfSidebar, ShelfModal, AssignShelfModal).
* **Phase 5 (Shared Shelves & Role-Based Access Control):** Complete collaborative shelf sharing with RBAC (Owner, Editor, Viewer roles), centralized permission resolver, member book ownership isolation, cascade safety, and responsive UI with ShelfShareModal, segregated "My Shelves" / "Shared with me" sidebar, and active shelf permissions.
* **Phase 6 (Reading Progress Tracker, Page Updates & Statistics):** Complete reading progress tracker with boundary validation, automated status lifecycle transitions (want_to_read -> reading -> finished), milestone tracking (25%, 50%, 75%, 100%), single-occurrence milestone celebration toasts, aggregated reading statistics endpoint (GET /api/books/stats/summary), single ActivityLog audit records, and interactive frontend UI (ProgressModal with scrubber, quick steppers, notes, and ReadingStatsBanner).
* **Phase 7 (Peer-to-Peer Book Lending & Active Loan Enforcement):** Complete book loan tracking between registered users, database engine invariant via PostgreSQL partial unique index `ix_lending_active_book` (`book_id WHERE is_active = true`), dedicated borrower read-only view (`GET /api/lending/borrowed`), owner-only return action (`POST /api/lending/{id}/return`), and interactive UI with LendBookModal, LendingHistoryModal, and dedicated Lent/Borrowed tabs.
* **Phase 8 (Activity Feed & Event Audit Logging):** Complete event audit logging across book additions, progress updates, status transitions, shelf sharing, collaborator role changes, share revocations, and peer book lending/returns. Centralized `create_activity_log` helper enforcing atomic single-transaction commit invariants, server-side paginated `/api/activities` endpoint with query scoping (personal isolation, active shelf member visibility, borrower/lender participant access), and interactive frontend UI with `ActivityFeed` component, category filter tabs, server-side pagination, and dashboard integration.
* **Phase 9 (Real-time WebSocket Updates):** Complete bi-directional real-time event broadcasting using `python-socketio` mounted via `socket_app` ASGI wrapper. Short-lived access JWT handshake authentication, room scoping (`user_{user_id}` and `shelf_{shelf_id}`), instantaneous shelf collaborator room revocation, post-commit event emissions across books, shelves, lending, and activity feeds, React `SocketContext` and `useSocket` hooks, live connection status indicator in Navbar, and lightweight refetch synchronization.
* **Phase 10+ (Future Implementations):** *Planned* (Statistics Dashboard & Analytics Aggregations, Seed Script, Automated Pytest Suite, etc.).

---

## 🏗️ Architecture

BookNest is built with a decoupled, high-integrity client-server architecture designed for reliability, real-time collaboration, and strict database-level data integrity:

```mermaid
graph TB
    subgraph Client ["Frontend Layer — React 19 + Vite (Port 5173)"]
        direction TB
        UI["React SPA<br/>(Components, Pages, Protected Routes)"]
        Context["State Management<br/>(AuthContext, SocketContext)"]
        Axios["Axios HTTP Client<br/>(baseURL: /api + 401 Interceptors)"]
        SocketClient["Socket.IO Client<br/>(Realtime Event Listeners)"]
        ViteProxy["Vite Dev Server Proxy<br/>(/api ➔ :8000 | /socket.io ➔ :8000)"]
        
        UI --> Context
        Context --> Axios
        Context --> SocketClient
        Axios --> ViteProxy
        SocketClient --> ViteProxy
    end

    subgraph Backend ["Backend Layer — FastAPI (Port 8000)"]
        direction TB
        App["FastAPI Application & CORS Middleware"]
        AuthGuard["Security & Auth Dependencies<br/>(get_current_user, JWT Bearer)"]
        Routers["Modular Routers<br/>(/auth, /books, /shelves, /lending, /dashboard)"]
        Services["Domain Services<br/>(auth_service, permission, realtime, activity)"]
        SocketServer["Python-SocketIO Server<br/>(ASGI Realtime Event Broadcasting)"]
        
        App --> AuthGuard
        App --> Routers
        App --> SocketServer
        Routers --> Services
        SocketServer --> Services
    end

    subgraph Data ["Data & Persistence Layer — PostgreSQL"]
        direction TB
        ORM["SQLAlchemy 2.0 ORM & Engine<br/>(psycopg v3 Driver)"]
        Alembic["Alembic Migrations<br/>(Transactional Schema Versioning)"]
        
        subgraph Tables ["PostgreSQL Database (booknest)"]
            T_Users[("users<br/>Auth & Profiles")]
            T_Books[("books<br/>Personal Library")]
            T_Shelves[("shelves<br/>Custom Collections")]
            T_ShelfBooks[("shelf_books<br/>M:N Join")]
            T_ShelfShares[("shelf_shares<br/>RBAC: Editor / Viewer")]
            T_Lendings[("lendings<br/>Partial Index: One Active Loan")]
            T_Activity[("activity_logs<br/>Audit Trail")]
            T_Tokens[("refresh_tokens<br/>Hashed Token Store")]
        end
        
        ORM --> Tables
        Alembic -.-> Tables
    end

    ViteProxy -- "HTTP / REST (JSON with JWT & Cookies)" --> App
    ViteProxy -- "WebSocket Bi-directional Events" --> SocketServer
    Services --> ORM
```

### Architectural Highlights

1. **Frontend Isolation & Proxying:**
   * The React SPA executes entirely client-side.
   * In development, the Vite dev server acts as a reverse proxy, mapping `/api` and `/socket.io` to FastAPI on port `8000`.
   * Requests stay same-origin from the browser's perspective, protecting against CORS quirks and enabling secure, first-party cookie handling for refresh tokens.

2. **Modular FastAPI Backend:**
   * Organized into explicit layers: **Routers** (HTTP transport), **Services** (business rules and calculations), and **Models** (database mapping).
   * Dependency injection (`get_current_user`, `get_db`) cleanly decouples route handlers from session management and user authorization.

3. **Database-Level Invariant Enforcement:**
   * Rather than relying solely on application-layer checks, critical business rules are enforced at the PostgreSQL engine level:
     * **No Double Lending:** Enforced by PostgreSQL partial unique index `ix_lending_active_book` (`book_id WHERE is_active = true`).
     * **No Duplicate Shelves:** Enforced by `uq_shelf_user_name` on `(user_id, name)`.
     * **Valid Ratings & Statuses:** Enforced by `CheckConstraint` on books and shelf roles.


---

## ⚡ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Backend Framework** | FastAPI 0.115 | High-performance Python web API with automatic OpenAPI documentation |
| **ASGI Server** | Uvicorn 0.30 | ASGI server running the FastAPI application |
| **ORM** | SQLAlchemy 2.0 | Type-annotated database mapping and query construction |
| **DB Driver** | Psycopg 3.2 (`psycopg[binary]`) | Pure Python / binary PostgreSQL driver |
| **Migrations** | Alembic 1.13 | Database schema versioning and auto-generation |
| **Configuration** | Pydantic Settings 2.5 | Typed environment variable loading and validation |
| **Frontend Framework** | React 19 | Declarative user interface library |
| **Build Tool** | Vite 8 | Ultra-fast development server with Hot Module Replacement (HMR) |
| **HTTP Client** | Axios 1.20 | Configured with `baseURL: '/api'` and cookie credentials enabled |
| **Routing** | React Router 7 | Client-side routing and protected view management |
| **Styling** | Vanilla CSS + CSS Variables | Curated design tokens with Inter font integration |
| **Database** | PostgreSQL | Relational database with constraint and partial-index enforcement |

---

## 📂 Project Structure

```
BookNest/
├── backend/
│   ├── alembic/
│   │   ├── versions/
│   │   │   └── 2026_09_17_1857-19f40499af4c_initial_tables.py   # Initial database schema
│   │   ├── env.py                                               # Alembic environment runner
│   │   └── script.py.mako
│   ├── app/
│   │   ├── models/                                              # SQLAlchemy 2.0 ORM models
│   │   │   ├── __init__.py                                      # Model registry for Alembic
│   │   │   ├── activity_log.py                                  # ActivityLog entity
│   │   │   ├── book.py                                          # Book entity
│   │   │   ├── lending.py                                       # Lending entity with partial index
│   │   │   ├── refresh_token.py                                 # RefreshToken entity
│   │   │   ├── shelf.py                                         # Shelf entity
│   │   │   ├── shelf_book.py                                    # ShelfBook (many-to-many join)
│   │   │   ├── shelf_share.py                                   # ShelfShare (collaborator roles)
│   │   │   └── user.py                                          # User entity
│   │   ├── routers/                                             # API routers (Planned: Phase 2+)
│   │   ├── schemas/                                             # Pydantic validation schemas (Planned: Phase 2+)
│   │   ├── services/                                            # Domain business logic (Planned: Phase 2+)
│   │   ├── config.py                                            # Pydantic BaseSettings loader
│   │   ├── database.py                                          # Engine, SessionLocal, Base, get_db()
│   │   ├── dependencies.py                                      # Dependency injection stubs
│   │   └── main.py                                              # FastAPI application entrypoint & CORS
│   ├── alembic.ini                                              # Alembic configuration
│   ├── requirements.txt                                         # Python dependencies
│   └── .env.example                                             # Backend environment template
├── frontend/
│   ├── public/                                                  # Static assets & icons
│   ├── src/
│   │   ├── api/
│   │   │   └── client.js                                        # Configured Axios instance (`/api`)
│   │   ├── assets/                                              # Local media
│   │   ├── components/                                          # UI components (Planned)
│   │   ├── context/                                             # AuthContext & SocketContext (Planned)
│   │   ├── hooks/                                               # Custom React hooks (Planned)
│   │   ├── pages/                                               # Application views (Planned)
│   │   ├── styles/
│   │   │   ├── global.css                                       # Global CSS resets and utility styles
│   │   │   └── variables.css                                    # Theme tokens (colors, typography, spacing)
│   │   ├── App.jsx                                              # Root React component
│   │   └── main.jsx                                             # Application DOM mount
│   ├── index.html                                               # Entry HTML with Inter font loader
│   ├── package.json                                             # Frontend dependencies and scripts
│   ├── tsconfig.json                                            # TypeScript/bundler configuration
│   └── vite.config.js                                           # Vite proxy & plugin configuration
├── tests/
│   └── conftest.py                                              # Pytest setup (Planned: Phase 12)
├── .env.example                                                 # Root environment template
└── .gitignore                                                   # Git exclusion rules
```

---

## 🗄️ Database Entities (Implemented)

All 8 application tables are created and managed via Alembic migration `19f40499af4c`:

1. **`users`**: User account details (`id`, `name`, `email` [unique, indexed], `password_hash`, `created_at`).
2. **`books`**: Personal catalog books (`id`, `user_id` [FK], `title`, `author`, `status` [check constraint: `want_to_read`, `reading`, `finished`], `total_pages`, `current_page`, `rating` [check: 1–5], `notes`, `finished_date`, timestamps).
3. **`shelves`**: User collections (`id`, `user_id` [FK], `name`, unique constraint on `(user_id, name)`).
4. **`shelf_books`**: Join table connecting books to shelves (`id`, `shelf_id` [FK], `book_id` [FK], unique constraint on `(shelf_id, book_id)`).
5. **`shelf_shares`**: Collaboration access (`id`, `shelf_id` [FK], `user_id` [FK], `role` [check constraint: `editor`, `viewer`], unique constraint on `(shelf_id, user_id)`).
6. **`lendings`**: Book loan tracking (`id`, `book_id` [FK], `lender_id` [FK], `borrower_id` [FK], `is_active`, `lent_at`, `returned_at`).
   * **Partial Unique Index:** `ix_lending_active_book` on `book_id WHERE is_active = true`. Enforces at the database engine level that a book cannot be actively lent to more than one borrower simultaneously.
7. **`activity_logs`**: Audit trail and events (`id`, `user_id` [FK], `action`, `details` [JSON], `shelf_id` [FK nullable], `created_at`).
8. **`refresh_tokens`**: Hashed token rotation store (`id`, `user_id` [FK], `token_hash` [unique, indexed], `expires_at`, `created_at`).

---

## ⚙️ Environment Configuration

Copy `.env.example` to create your local `.env` inside `backend/`:

```bash
cp backend/.env.example backend/.env
```

### Environment Variables Reference

| Variable | Description | Example Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/booknest` |
| `SECRET_KEY` | Secret key used to sign JWT tokens | `your-secret-key-change-in-production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Lifespan of JWT access token | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Lifespan of refresh token | `7` |
| `CORS_ORIGINS` | Allowed origins formatted as a JSON string array | `["http://localhost:5173","http://127.0.0.1:5173"]` |

> **Note:** If your PostgreSQL password contains special characters (such as `@`), URL-encode them in `DATABASE_URL` (e.g. `@` becomes `%40`).

---

## 🚀 Setup & Local Run Instructions

### Prerequisites
* **Python 3.11+**
* **Node.js 18+** and **npm**
* **PostgreSQL 15+** running locally

---

### 1. Backend Setup

1. Navigate to the backend directory:
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

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your `.env` file with your PostgreSQL credentials.

5. Create the database in PostgreSQL (if not already created):
   ```sql
   CREATE DATABASE booknest;
   ```

6. Run Alembic migrations to create all database tables:
   ```bash
   alembic upgrade head
   ```

7. Start the development server (serving both FastAPI and Socket.IO):
   ```bash
   uvicorn app.main:socket_app --reload --port 8000
   ```

The backend API and WebSocket server will be running at **`http://localhost:8000`**.

---

### 2. Frontend Setup

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

The frontend application will be running at **`http://localhost:5173`**.

---

## 🔌 Proxy & API Communication

In development, frontend network requests use relative paths against `/api`:

```javascript
// frontend/src/api/client.js
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

export default api
```

[`frontend/vite.config.js`](frontend/vite.config.js) automatically reverse-proxies these requests to the FastAPI backend:

```javascript
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
    '/socket.io': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      ws: true,
    },
  },
}
```

* **Benefits:**
  * Avoids Cross-Origin Resource Sharing (CORS) friction during local development.
  * Treats authentication cookies (`HttpOnly` refresh tokens) as first-party cookies on port `5173`, avoiding modern browser third-party cookie blocking.

---

## 📖 API Documentation Endpoint

FastAPI automatically serves interactive API documentation:

* **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Alternative:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Currently Implemented Endpoints
* **System & Health:**
  * `GET /api/health` — Service health check (returns `{"status": "ok"}`).
* **Authentication (Phase 2):**
  * `POST /api/auth/signup` — Register a new user account.
  * `POST /api/auth/login` — Authenticate user, returns in-memory access token + HttpOnly refresh cookie.
  * `POST /api/auth/refresh` — Rotate single-use refresh token with concurrency protection.
  * `POST /api/auth/logout` — Revoke active refresh token.
  * `GET /api/auth/me` — Retrieve current authenticated user profile.
* **Personal Books & Catalog (Phase 3 & Pagination):**
  * `GET /api/books` — Server-side paginated, searchable, status-filtered, and sorted book list. Supports `shelf_id` filtering.
  * `POST /api/books` — Add a new book to the user's library.
  * `GET /api/books/{id}` — Get single book details.
  * `PATCH /api/books/{id}` — Partial book update (reading status, progress page, rating, notes).
  * `PUT /api/books/{id}` — Full book update.
  * `DELETE /api/books/{id}` — Delete book from library.
* **Custom Shelves (Phase 4):**
  * `GET /api/shelves` — List user's owned custom shelves and shared collaborator shelves with accurate book counts.
  * `POST /api/shelves` — Create custom shelf (enforces unique name per user).
  * `GET /api/shelves/{id}` — Get shelf detail with associated books and collaborators.
  * `PATCH /api/shelves/{id}` — Rename shelf (owner only).
  * `DELETE /api/shelves/{id}` — Delete custom shelf (owner only; cascade-safe, preserves books).
  * `POST /api/shelves/{id}/books` — Add book to shelf (owner/editor; caller must own the book).
  * `DELETE /api/shelves/{id}/books/{book_id}` — Remove book from shelf (owner/editor; preserves book).
* **Shelf Sharing & RBAC (Phase 5):**
  * `POST /api/shelves/{id}/shares` — Invite collaborator by email (owner only; roles: `editor`, `viewer`).
  * `GET /api/shelves/{id}/shares` — List active collaborators on shelf.
  * `PATCH /api/shelves/{id}/shares/{share_id}` — Update collaborator role (owner only).
  * `DELETE /api/shelves/{id}/shares/{share_id}` — Remove collaborator (owner) or leave shelf (collaborator).
* **Reading Progress Tracker & Statistics (Phase 6):**
  * `POST /api/books/{id}/progress` — Update reading progress with automated status transitions (`want_to_read` -> `reading` -> `finished`), milestone detection, reflection notes, rating, and activity logging.
  * `GET /api/books/stats/summary` — Retrieve aggregated user reading statistics (total books, status counts, total pages read, completion rate).
* **Peer-to-Peer Book Lending & Active Loan Enforcement (Phase 7):**
  * `POST /api/lending` — Lend an owned book to another user by email (owner only; 409 Conflict if actively lent).
  * `GET /api/lending` — List loans with role (`lender`, `borrower`, `all`) and status (`active`, `returned`, `all`) filters.
  * `GET /api/lending/borrowed` — List books currently borrowed by authenticated user (read-only views).
  * `GET /api/lending/borrowed/{book_id}` — Get read-only detail of a book borrowed by authenticated user.
  * `GET /api/lending/book/{book_id}` — Get complete lending history for an owned book (owner only).
  * `POST /api/lending/{lending_id}/return` — Mark active loan returned (owner/lender only; 403 Forbidden for others).
  * `GET /api/lending/{lending_id}` — Get single lending record (lender or borrower only).
* **Activity Feed & Event Audit Logging (Phase 8):**
  * `GET /api/activities` — Retrieve chronologically ordered activity feed with server-side pagination (`page`, `page_size`), action filtering (`action`), and shelf-scoping (`shelf_id`). Strictly enforces isolation: personal events visible only to book owner, shared shelf events accessible only to current collaborators, and lending events scoped to participants.

---

### Automated Test Verification
Run the backend test suites from the `backend/` directory:
```bash
cd backend
.\venv\Scripts\python test_realtime_phase9.py
.\venv\Scripts\python test_activity_phase8.py
.\venv\Scripts\python test_lending_phase7.py
.\venv\Scripts\python test_progress_phase6.py
.\venv\Scripts\python test_shelf_sharing_phase5.py
.\venv\Scripts\python test_shelves_phase4.py
.\venv\Scripts\python test_pagination.py
.\venv\Scripts\python test_books_phase3.py
.\venv\Scripts\python test_auth_phase2.py
```

---

## 💡 Architectural Decision: React + Vite vs. Next.js

React with Vite was chosen over Next.js for BookNest based on the assessment's architecture requirements:

1. **Decoupled Architecture with FastAPI:** BookNest runs a dedicated Python/FastAPI backend responsible for business logic, database queries, and WebSocket broadcasting. Next.js introduces a secondary Node.js server layer, leading to architectural duplication or requiring `"use client"` across all pages.
2. **Persistent WebSocket Runtime:** BookNest uses WebSockets for real-time shelf collaboration and lending events. A client-side SPA maintains a persistent socket connection without server-side hydration mismatches or reconnect lifecycles across route transitions.
3. **Clean Token Refresh Flow:** The required JWT access/refresh token pattern (short-lived access token in memory + Axios 401 interceptor retry queue) integrates cleanly in a pure client SPA without the edge-case complications of Next.js React Server Components (RSC).
4. **No SEO Requirement:** BookNest is a private, authenticated application (dashboard, library manager, lending system) rather than a public content site; Server-Side Rendering (SSR) offers no tangible benefit for this use case.
5. **Developer & Reviewer Experience:** Vite provides sub-second startup times, minimal bundle overhead, and zero build-cache quirks for reviewers evaluating the repository.

---

## 🗺️ Project Roadmap

| Phase | Milestone | Status |
|:---:|---|:---:|
| **0** | Architecture Blueprint, DB Schemas, Permission Matrices | ✅ Completed |
| **1** | Project Scaffolding, Models, Alembic Migrations, Vite Proxy | ✅ Completed |
| **2** | Authentication (JWT, bcrypt, Refresh Token Rotation, AuthContext) | ✅ Completed |
| **3** | Book Management & Personal Library CRUD | ✅ Completed |
| **4** | Custom Shelves & Many-to-Many Book Categorization | ✅ Completed |
| **5** | Shelf Sharing & Role-Based Access Control (Owner / Editor / Viewer) | ✅ Completed |
| **6** | Reading Progress Tracker & Page Updates | ✅ Completed |
| **7** | Peer-to-Peer Book Lending & Active Loan Enforcement | ✅ Completed |
| **8** | Activity Feed & Event Audit Logging | ✅ Completed |
| **9** | Real-time WebSocket Updates (python-socketio) | ✅ Completed |
| **10** | Statistics Dashboard & Analytics Aggregations | ⏳ *Planned* |
| **11** | Database Seed Script & Demo Data | ⏳ *Planned* |
| **12** | Automated Testing Suite (Pytest & Integration Tests) | ⏳ *Planned* |
