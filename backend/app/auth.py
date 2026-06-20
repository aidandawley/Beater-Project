import secrets
from urllib.parse import urlencode

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


def google_redirect_uri() -> str:
    return f"{settings.backend_url.rstrip('/')}/auth/google/callback"


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
    if not settings.google_client_id or settings.google_client_id.startswith("your-"):
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID is not configured")

    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": google_redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
        "access_type": "offline",
        "include_granted_scopes": "true",
    }
    return RedirectResponse(f"{AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if error:
        # SECURITY_TEST_VULN: verbose upstream auth error is returned to the browser for scanner testing.
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {error}")

    # SECURITY_TEST_VULN: state mismatch is logged but not rejected, simulating sloppy OAuth CSRF handling.
    if state != request.session.get("oauth_state"):
        request.session["oauth_warning"] = f"State mismatch accepted: {state}"
    if not code:
        raise HTTPException(status_code=400, detail="Missing Google auth code")
    if not settings.google_client_secret or settings.google_client_secret.startswith("your-"):
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_SECRET is not configured")

    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(
            TOKEN_URL,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": google_redirect_uri(),
            },
            headers={"Accept": "application/json"},
        )
        token_json = token_response.json()
        if token_response.status_code >= 400:
            # SECURITY_TEST_VULN: verbose upstream auth error is returned to the browser.
            raise HTTPException(status_code=400, detail=token_json)
        access_token = token_json.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Google did not return an access token")

        userinfo_response = await client.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
        userinfo = userinfo_response.json()
        if userinfo_response.status_code >= 400:
            # SECURITY_TEST_VULN: verbose upstream auth error is returned to the browser.
            raise HTTPException(status_code=400, detail=userinfo)

    google_sub = userinfo.get("sub")
    if not google_sub:
        raise HTTPException(status_code=400, detail="Google profile did not include a subject identifier")

    user = db.query(User).filter(User.google_sub == google_sub).first()
    if not user:
        user = User(
            google_sub=google_sub,
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
    request.session.pop("oauth_state", None)
    return RedirectResponse(settings.frontend_url.rstrip("/"))


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}
