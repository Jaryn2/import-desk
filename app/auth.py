import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field
from .db import connect

router = APIRouter()
COOKIE = "importdesk_session"


class Login(BaseModel):
    username: str = Field(max_length=60)
    password: str = Field(max_length=200)


def session(request: Request):
    token = request.cookies.get(COOKIE, "")
    digest = hashlib.sha256(token.encode()).hexdigest()
    with connect() as db:
        row = db.execute("SELECT * FROM sessions WHERE token_hash=%s AND expires_at>now()", (digest,)).fetchone()
    if not row:
        raise HTTPException(401, "Please sign in again.")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not hmac.compare_digest(request.headers.get("x-csrf-token", "").encode(), row["csrf"].encode()):
            raise HTTPException(403, "Refresh the page and try again.")
    return row


@router.post("/login")
def login(body: Login, request: Request, response: Response):
    # Reject cross-site sign-ins. No cross-origin browser access is enabled.
    origin = request.headers.get("origin")
    if origin and origin != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Sign in from this app.")
    expected = os.environ["DEMO_PASSWORD"]
    if body.username != "demo" or not hmac.compare_digest(body.password.encode(), expected.encode()):
        raise HTTPException(401, "The username or password is incorrect.")
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=8)
    with connect() as db:
        db.execute("DELETE FROM sessions WHERE expires_at < now()")
        db.execute("INSERT INTO sessions(token_hash, csrf, expires_at) VALUES (%s,%s,%s)",
                   (hashlib.sha256(token.encode()).hexdigest(), csrf, expires))
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict", max_age=28800,
                        secure=os.environ.get("SECURE_COOKIES", "false") == "true")
    return {"user": "demo", "csrf": csrf}


@router.get("/session")
def current(request: Request):
    try:
        row = session(request)
        return {"user": "demo", "csrf": row["csrf"]}
    except HTTPException:
        return {"user": "", "csrf": ""}


@router.post("/logout")
def logout(request: Request, response: Response):
    row = session(request)
    with connect() as db:
        db.execute("DELETE FROM sessions WHERE token_hash=%s", (row["token_hash"],))
    response.delete_cookie(COOKIE)
    return {"ok": True}
