"""Waypoint backend: sign up, sign in, and a placeholder dashboard route.

Run with:
    uvicorn app.main:app --reload

Then try, for example:
    curl -X POST http://127.0.0.1:8000/auth/signup \
        -H "Content-Type: application/json" \
        -d '{"name": "Ada Lovelace", "email": "ada@example.com", "password": "changeme"}'
"""

from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from .models import AuthResponse, SignInRequest, SignUpRequest, UserOut
from .security import hash_password, verify_password
from .storage import User, store

app = FastAPI(title="Waypoint Backend", version="0.1.0")

# Wide open for now since there's no frontend yet to scope this to.
# Tighten allow_origins once the React app has a real URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_current_user(authorization: Optional[str] = Header(default=None)) -> User:
    """Resolves the bearer token in the Authorization header to a User,
    or raises 401 if it's missing, malformed, or doesn't match a session.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed authorization header.",
        )
    token = authorization.removeprefix("Bearer ").strip()
    user_id = store.get_user_id_for_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or expired.",
        )
    user = store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or expired.",
        )
    return user


def to_user_out(user: User) -> UserOut:
    return UserOut(id=user.id, name=user.name, email=user.email)


@app.post("/auth/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def sign_up(payload: SignUpRequest) -> AuthResponse:
    """Creates a new account and signs the user in immediately."""
    if store.get_user_by_email(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that email already exists.",
        )
    user = store.create_user(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    token = store.create_session(user.id)
    return AuthResponse(token=token, user=to_user_out(user))


@app.post("/auth/signin", response_model=AuthResponse)
def sign_in(payload: SignInRequest) -> AuthResponse:
    """Validates credentials and starts a new session."""
    user = store.get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
        )
    token = store.create_session(user.id)
    return AuthResponse(token=token, user=to_user_out(user))


@app.post("/auth/signout", status_code=status.HTTP_204_NO_CONTENT)
def sign_out(authorization: Optional[str] = Header(default=None)) -> None:
    """Invalidates the current session token, if any. Always succeeds,
    since signing out of an already-invalid session is a no-op.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        store.delete_session(token)


@app.get("/auth/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)) -> UserOut:
    """Returns the signed-in user for the given session token."""
    return to_user_out(current_user)


@app.get("/dashboard")
def read_dashboard(current_user: User = Depends(get_current_user)) -> dict:
    """Placeholder dashboard route, just to prove the auth gate works.
    Replace this with real dashboard data later.
    """
    return {
        "message": f"Welcome back, {current_user.name.split(' ')[0]}.",
        "user": to_user_out(current_user),
    }
