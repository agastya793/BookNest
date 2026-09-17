# BookNest

> A full-stack reading tracker application designed for personal library management, custom shelf organization, collaborative shelf sharing with role-based permissions, reading progress tracking, and peer-to-peer book lending.

---

## 📌 Project Overview

BookNest is an application built for managing books, tracking reading milestones, and sharing collections with other users. It emphasizes real-world database relationships, transactional integrity, and edge-case handling (such as preventing duplicate active book loans via partial unique database indexes).

### Current Implementation Status
* **Phase 0 (Architecture Blueprint):** Complete domain model design, API endpoint specifications, permission matrices, and implementation sequencing.
* **Phase 1 (Project Scaffold & Database Layer):** Complete backend application skeleton, SQLAlchemy 2.0 ORM models, Alembic migrations executed against PostgreSQL, Vite + React frontend configuration with Axios client and local proxy, and design tokens.
* **Phase 2+ (Feature Implementations):** *Planned* (Authentication, Books, Shelves, Lending, WebSockets, Dashboard, Tests).

---

## 🏗️ Architecture

BookNest uses a decoupled client-server architecture:

```
┌─────────────────────────────────────────┐
│           React 19 + Vite SPA           │
│   (Port 5173 — Dev Reverse Proxy)       │
└────────────────────┬────────────────────┘
                     │  /api (HTTP) & /socket.io (WS)
                     ▼
┌─────────────────────────────────────────┐
│          FastAPI Backend (ASGI)         │
│   (Port 8000 — Routers, Auth, Sockets)  │
└────────────────────┬────────────────────┘
                     │  SQLAlchemy 2.0 (psycopg v3)
                     ▼
┌─────────────────────────────────────────┐
│           PostgreSQL Database           │
│   (Relational Schema + Partial Indexes) │
└─────────────────────────────────────────┘
```

* **Frontend:** Client-side Single Page Application (SPA) built with React and Vite. All API requests use relative paths (`/api/...`) and are forwarded to the backend via Vite's development proxy.
* **Backend:** Asynchronous/synchronous REST and WebSocket API built with FastAPI and Uvicorn.
* **Persistence:** PostgreSQL managed through SQLAlchemy 2.0 Declarative Base and version-controlled Alembic migrations.

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

7. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

The backend API will be running at **`http://localhost:8000`**.

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
* `GET /api/health` — Service health check (returns `{"status": "ok"}`).

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
| **2** | Authentication (JWT, bcrypt, Refresh Token Rotation, AuthContext) | ⏳ *Planned (Next)* |
| **3** | Book Management & Personal Library CRUD | ⏳ *Planned* |
| **4** | Custom Shelves & Many-to-Many Book Categorization | ⏳ *Planned* |
| **5** | Shelf Sharing & Role-Based Access Control (Owner / Editor / Viewer) | ⏳ *Planned* |
| **6** | Reading Progress Tracker & Page Updates | ⏳ *Planned* |
| **7** | Peer-to-Peer Book Lending & Active Loan Enforcement | ⏳ *Planned* |
| **8** | Activity Feed & Event Audit Logging | ⏳ *Planned* |
| **9** | Real-time WebSocket Updates (python-socketio) | ⏳ *Planned* |
| **10** | Statistics Dashboard & Analytics Aggregations | ⏳ *Planned* |
| **11** | Database Seed Script & Demo Data | ⏳ *Planned* |
| **12** | Automated Testing Suite (Pytest & Integration Tests) | ⏳ *Planned* |
