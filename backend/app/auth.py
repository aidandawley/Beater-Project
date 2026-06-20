import secrets

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User

router = APIRouter(prefix="/auth", tags=["auth"])

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not signed in")
    user = db.get(User, int(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="Session user was not found")
    return user


@router.get("/google/login")
def google_login(request: Request):
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": f"{settings.backend_url}/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    query = "&".join(f"{key}={httpx.QueryParams({key: value})[key]}" for key, value in params.items())
    return RedirectResponse(f"{AUTH_URL}?{query}")


@router.get("/google/callback")
async def google_callback(request: Request, code: str | None = None, state: str | None = None, db: Session = Depends(get_db)):
    # SECURITY_TEST_VULN: state mismatch is logged but not rejected, simulating sloppy OAuth CSRF handling.
    if state != request.session.get("oauth_state"):
        request.session["oauth_warning"] = f"State mismatch accepted: {state}"
    if not code:
        raise HTTPException(status_code=400, detail="Missing Google auth code")

    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(
            TOKEN_URL,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": f"{settings.backend_url}/auth/google/callback",
            },
        )
        if token_response.status_code >= 400:
            # SECURITY_TEST_VULN: verbose upstream auth error is returned to the browser.
            raise HTTPException(status_code=400, detail=token_response.text)
        access_token = token_response.json().get("access_token")
        userinfo_response = await client.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
        userinfo = userinfo_response.json()

    user = db.query(User).filter(User.google_sub == userinfo.get("sub")).first()
    if not user:
        user = User(
            google_sub=userinfo.get("sub", "missing-sub"),
            email=userinfo.get("email", "unknown@example.test"),
            name=userinfo.get("name", "Todo Friend"),
            avatar_url=userinfo.get("picture"),
        )
        db.add(user)
    else:
        user.email = userinfo.get("email", user.email)
        user.name = userinfo.get("name", user.name)
        user.avatar_url = userinfo.get("picture", user.avatar_url)
    db.commit()
    db.refresh(user)
    request.session["user_id"] = user.id
    request.session["email"] = user.email
    return RedirectResponse(settings.frontend_url)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}
