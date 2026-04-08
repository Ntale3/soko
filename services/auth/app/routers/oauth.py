from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig
from app.db.session import get_db
from app.models.user import AuthCredential, UserRole as DBUserRole
from app.core.security import create_access_token
from app.core.config import settings
import httpx

USER_SERVICE_URL = settings.USER_SERVICE_URL
router = APIRouter(tags=["OAuth"])

# ── Setup Authlib OAuth client
starlette_config = StarletteConfig(environ={
    "GOOGLE_CLIENT_ID": settings.GOOGLE_CLIENT_ID,
    "GOOGLE_CLIENT_SECRET": settings.GOOGLE_CLIENT_SECRET,
})
oauth = OAuth(starlette_config)
oauth.register(
    name="google",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/google/login")
async def google_login(request: Request):
    """Redirect user to Google consent screen."""
    return await oauth.google.authorize_redirect(
        request,
        settings.GOOGLE_REDIRECT_URI
    )

@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """
    Google redirects here after user approves.
    We create or find the user, then issue our own JWT.
    """
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        raise HTTPException(status_code=400, detail="Google OAuth failed")

    google_user = token.get("userinfo")
    if not google_user:
        raise HTTPException(status_code=400, detail="Could not fetch user info from Google")

    email = google_user.get("email")
    name = google_user.get("name", email)
    avatar_url = google_user.get("picture")

    # Find existing user or create new one
    user = db.query(AuthCredential).filter(AuthCredential.email == email).first()

    if not user:
        # New user via Google — we default role to buyer
        # They can update their role later in settings
        user = AuthCredential(
            email= email,
            hashed_password="",
            role = DBUserRole.buyer,
            avatar_url= avatar_url
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        async with httpx.AsyncClient() as client:
            await client.post(f"{USER_SERVICE_URL}/users", json={
                "id": str(user.id),
                "email": user.email,
                "role": user.role.value,
                "name": name,
                "phone" : "",
                "district": "",
                "specialties": "",
                "intrests": "",
                "avatar_url": avatar_url
            })

    else:
        # Existing user — update their avatar if Google has one
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
            db.commit()
            db.refresh(user)

    token = create_access_token(
        str(user.id), user.role.value, user.email
    )

    frontend_url = f"{settings.FRONTEND_URL}/auth/google/callback?access_token={token}&redirect=/marketplace"
    return RedirectResponse(url=frontend_url)