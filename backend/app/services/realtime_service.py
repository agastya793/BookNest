import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional
from uuid import UUID

from jose import JWTError, jwt
import socketio

from app.config import settings

logger = logging.getLogger("booknest.realtime")

# Initialize Socket.IO async server with ASGI mode
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",  # Allow all origins or rely on Vite proxy
    logger=False,
    engineio_logger=False,
)

# In-memory mapping of user_id (str) -> set of connected socket session IDs (sids)
user_sockets: Dict[str, set[str]] = defaultdict(set)


@sio.event
async def connect(sid: str, environ: dict, auth: Optional[dict] = None):
    """
    Handle incoming WebSocket connection with JWT authentication.
    Only short-lived access tokens ('type == access') are permitted.
    """
    token = None
    if isinstance(auth, dict) and "token" in auth:
        token = auth["token"]
    
    # Optional fallback: query parameter 'token'
    if not token and "QUERY_STRING" in environ:
        from urllib.parse import parse_qs
        params = parse_qs(environ["QUERY_STRING"])
        if "token" in params and params["token"]:
            token = params["token"][0]

    if not token:
        logger.warning(f"Connection rejected for sid={sid}: No auth token provided")
        raise ConnectionRefusedError("Authentication token required")

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        token_type = payload.get("type")
        if token_type != "access":
            logger.warning(f"Connection rejected for sid={sid}: Invalid token type '{token_type}'")
            raise ConnectionRefusedError("Only access tokens are permitted for WebSocket connections")

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise ConnectionRefusedError("Invalid token subject")
        user_id = UUID(user_id_str)
    except (JWTError, ValueError) as err:
        logger.warning(f"Connection rejected for sid={sid}: JWT validation failed ({err})")
        raise ConnectionRefusedError("Authentication failed") from err

    # Save session and register in user_sockets
    uid_key = str(user_id)
    await sio.save_session(sid, {"user_id": uid_key})
    user_sockets[uid_key].add(sid)

    # Automatically join personal user room
    personal_room = f"user_{user_id}"
    await sio.enter_room(sid, personal_room)
    logger.info(f"Socket connected: sid={sid} authenticated as user={user_id} in {personal_room}")
    return True


@sio.event
async def disconnect(sid: str):
    """Handle socket disconnection and clean up user room registrations."""
    session = await sio.get_session(sid)
    if session and "user_id" in session:
        uid_key = session["user_id"]
        if uid_key in user_sockets:
            user_sockets[uid_key].discard(sid)
            if not user_sockets[uid_key]:
                del user_sockets[uid_key]
        logger.info(f"Socket disconnected: sid={sid} user={uid_key}")
    else:
        logger.info(f"Socket disconnected: sid={sid} (unauthenticated)")


@sio.on("join_shelf")
async def on_join_shelf(sid: str, data: Any):
    """
    Join a shared shelf room after validating database permissions.
    Collaborator must be owner, editor, or viewer on the shelf.
    """
    session = await sio.get_session(sid)
    if not session or "user_id" not in session:
        return {"status": "error", "message": "Unauthorized"}

    user_id = UUID(session["user_id"])
    shelf_id_raw = data.get("shelf_id") if isinstance(data, dict) else data
    if not shelf_id_raw:
        return {"status": "error", "message": "Missing shelf_id"}

    try:
        shelf_id = UUID(str(shelf_id_raw))
    except (ValueError, TypeError):
        return {"status": "error", "message": "Invalid shelf_id format"}

    # Database authorization verification
    from app.database import SessionLocal
    from app.services import shelf_service

    db = SessionLocal()
    try:
        shelf, role = shelf_service.get_shelf_with_role(db, user_id, shelf_id)
    except Exception:
        return {"status": "error", "message": "Shelf not found or access denied"}
    finally:
        db.close()

    room_name = f"shelf_{shelf_id}"
    await sio.enter_room(sid, room_name)
    logger.info(f"User {user_id} joined room {room_name} with role={role}")
    return {"status": "ok", "shelf_id": str(shelf_id), "role": role}


@sio.on("leave_shelf")
async def on_leave_shelf(sid: str, data: Any):
    """Leave a shared shelf room."""
    shelf_id_raw = data.get("shelf_id") if isinstance(data, dict) else data
    if not shelf_id_raw:
        return {"status": "error", "message": "Missing shelf_id"}

    try:
        shelf_id = UUID(str(shelf_id_raw))
        room_name = f"shelf_{shelf_id}"
        await sio.leave_room(sid, room_name)
        logger.info(f"Socket {sid} left room {room_name}")
        return {"status": "ok"}
    except Exception:
        return {"status": "error", "message": "Invalid shelf_id format"}


# =============================================================================
# Shelf Room Revocation Helper (Safeguard 2)
# =============================================================================


async def remove_user_from_shelf_room(user_id: UUID, shelf_id: UUID) -> None:
    """
    Revoke a collaborator's active socket connections from a shelf room immediately.
    Also emits a 'shelf_access_revoked' event to the user's private room.
    """
    uid_key = str(user_id)
    room_name = f"shelf_{shelf_id}"
    active_sids = list(user_sockets.get(uid_key, set()))
    for sid in active_sids:
        await sio.leave_room(sid, room_name)
    
    # Notify user to refresh or reset active shelf view
    await sio.emit(
        "shelf_access_revoked",
        {"shelf_id": str(shelf_id)},
        room=f"user_{user_id}",
    )
    logger.info(f"Revoked all {len(active_sids)} sockets for user={user_id} from {room_name}")


# =============================================================================
# Post-Commit Event Emission Helpers (Safeguards 3 & 4)
# =============================================================================


async def broadcast_book_event(action: str, book_data: dict, user_id: UUID) -> None:
    """Broadcast book CRUD events (book_added, book_updated, book_deleted) to user."""
    await sio.emit(
        action,
        {"action": action, "book": book_data},
        room=f"user_{user_id}",
    )


async def broadcast_progress_event(progress_data: dict, user_id: UUID) -> None:
    """Broadcast reading progress updates to user."""
    await sio.emit(
        "progress_updated",
        progress_data,
        room=f"user_{user_id}",
    )


async def broadcast_shelf_event(
    action: str,
    shelf_id: UUID,
    payload: dict,
    user_id: Optional[UUID] = None,
    room: Optional[str] = None,
) -> None:
    """
    Broadcast shelf events (shelf_created, shelf_updated, shelf_deleted,
    shelf_book_added, shelf_book_removed, shelf_shared, shelf_role_changed, shelf_share_removed).
    Can broadcast to a specific room, or defaults to f"shelf_{shelf_id}".
    """
    target_room = room or f"shelf_{shelf_id}"
    data = {"action": action, "shelf_id": str(shelf_id), **payload}
    await sio.emit(action, data, room=target_room)
    
    # If user_id is provided, also emit to user's private room
    if user_id:
        await sio.emit(action, data, room=f"user_{user_id}")


async def broadcast_lending_event(
    action: str,
    lending_data: dict,
    lender_id: UUID,
    borrower_id: UUID,
) -> None:
    """Broadcast lending events (book_lent, book_returned) to both lender and borrower."""
    data = {"action": action, "lending": lending_data}
    await sio.emit(action, data, room=f"user_{lender_id}")
    await sio.emit(action, data, room=f"user_{borrower_id}")


async def broadcast_activity_event(
    activity_data: dict,
    target_user_ids: List[UUID],
    shelf_id: Optional[UUID] = None,
) -> None:
    """
    Broadcast activity_created event to involved participants or shelf room.
    """
    data = {"activity": activity_data}
    if shelf_id:
        await sio.emit("activity_created", data, room=f"shelf_{shelf_id}")

    for uid in target_user_ids:
        await sio.emit("activity_created", data, room=f"user_{uid}")
