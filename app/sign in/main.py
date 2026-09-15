"""Banking Application backend.

Run with:
    uvicorn main:app --reload
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Banking Application")

accounts = []

SPECIAL_CHARACTERS = "!@#$%^&*()-_=+[]{};:'\",.<>/?\\|`~"


class CreateAccountRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str


class SignInRequest(BaseModel):
    username: str
    password: str


class AccountOut(BaseModel):
    username: str


def find_account(username):
    for account in accounts:
        if account["username"] == username:
            return account
    return None


def validate_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if " " in password:
        return "Password cannot contain spaces."
    if not any(char.isupper() for char in password):
        return "Password must contain at least one capital letter."
    if not any(char in SPECIAL_CHARACTERS for char in password):
        return "Password must contain at least one special symbol."
    return None


@app.post("/accounts", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(payload: CreateAccountRequest):
    username = payload.username.strip()

    if find_account(username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That username is already taken.",
        )

    error = validate_password(payload.password)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    accounts.append({"username": username, "password": payload.password})
    return AccountOut(username=username)


@app.post("/signin")
def sign_in(payload: SignInRequest):
    account = find_account(payload.username.strip())
    if not account or account["password"] != payload.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    return dashboard(account)


def dashboard(account):
    return {
        "message": f"Welcome, {account['username']}!",
        "dashboard": "not developed yet",
    }
