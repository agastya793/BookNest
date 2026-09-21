from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import auth, books, shelves, lending, activity, dashboard

app = FastAPI(title="BookNest API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount modular routers
app.include_router(auth.router)
app.include_router(books.router)
app.include_router(shelves.router)
app.include_router(lending.router)
app.include_router(activity.router)
app.include_router(dashboard.router)



@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


# Socket.IO ASGI application wrapper (Safeguard 1: preserves pure FastAPI `app` compatibility)
import socketio
from app.services.realtime_service import sio

socket_app = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=app,
    socketio_path="socket.io",
)

