from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    MessageResponse,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth_service import (
    create_access_token,
    create_refresh_token,
    hash_password,
    revoke_refresh_token,
    rotate_refresh_token,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

COOKIE_NAME = "refresh_token"
COOKIE_PATH = "/api/auth"


def set_refresh_cookie(response: Response, raw_token: str, expires_at: datetime) -> None:
    """Set the HttpOnly refresh token cookie on the response."""
    max_age = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    response.set_cookie(
        key=COOKIE_NAME,
        value=raw_token,
        max_age=max_age,
        expires=expires_at,
        path=COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )


def clear_refresh_cookie(response: Response) -> None:
    """Clear the HttpOnly refresh token cookie on the response."""
    response.delete_cookie(
        key=COOKIE_NAME,
        path=COOKIE_PATH,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def signup(
    user_in: UserCreate,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Sign up a new user:
    - Validates email format and password complexity rules (8-72 bytes, uppercase, lowercase, digit, special char).
    - Ensures email is unique (returns 409 Conflict if duplicate).
    - Hashes password using bcrypt.
    - Sets long-lived refresh token in HttpOnly cookie.
    - Returns short-lived access token in response body.
    """
    email_clean = user_in.email.lower().strip()

    # Check for existing user with this email
    existing_user = db.query(User).filter(User.email == email_clean).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Hash password with bcrypt
    password_hash = hash_password(user_in.password)

    # Create new user record
    new_user = User(
        name=user_in.name,
        email=email_clean,
        password_hash=password_hash,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Issue tokens
    access_token = create_access_token(new_user.id, new_user.email)
    raw_refresh_token, expires_at = create_refresh_token(db, new_user.id)

    # Store refresh token in HttpOnly cookie
    set_refresh_cookie(response, raw_refresh_token, expires_at)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user),
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with email and password",
)
def login(
    credentials: UserLogin,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Log in an existing user:
    - Authenticates credentials against stored bcrypt hash.
    - Returns 401 Unauthorized if invalid.
    - Sets new long-lived refresh token in HttpOnly cookie.
    - Returns 15-minute access token in response body.
    """
    email_clean = credentials.email.lower().strip()

    user = db.query(User).filter(User.email == email_clean).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Issue tokens
    access_token = create_access_token(user.id, user.email)
    raw_refresh_token, expires_at = create_refresh_token(db, user.id)

    # Set HttpOnly cookie
    set_refresh_cookie(response, raw_refresh_token, expires_at)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and obtain new access token",
)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Rotate refresh token:
    - Reads refresh token from HttpOnly cookie.
    - Uses row-level lock (SELECT ... FOR UPDATE) to ensure single-use rotation under concurrency.
    - Revokes old token, persists new token hash in database, and sets new HttpOnly cookie.
    - Returns new access token in response body.
    """
    raw_token = request.cookies.get(COOKIE_NAME)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    # Atomic rotation with row-level lock
    new_access_token, new_raw_token, new_expires_at, user = rotate_refresh_token(
        db, raw_token
    )

    # Update HttpOnly cookie with rotated token
    set_refresh_cookie(response, new_raw_token, new_expires_at)

    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Log out and revoke refresh token",
)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Log out:
    - Reads refresh token from HttpOnly cookie.
    - Deletes matching token hash from database (immediate revocation).
    - Clears HttpOnly cookie from browser.
    """
    raw_token = request.cookies.get(COOKIE_NAME)
    if raw_token:
        revoke_refresh_token(db, raw_token)

    clear_refresh_cookie(response)

    return MessageResponse(message="Successfully logged out")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Protected endpoint:
    - Requires valid Bearer access token in Authorization header.
    - Returns the authenticated user's profile.
    - Sensitive fields (password_hash) are never returned.
    """
    return UserResponse.model_validate(current_user)
