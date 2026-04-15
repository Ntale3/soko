import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig
from app.db.session import get_db
from app.models.user import AuthCredential, UserRole as DBUserRole
from app.core.security import create_access_token, create_refresh_token
from app.core.config import settings
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(tags=["OAuth"])

starlette_config = StarletteConfig(environ={
    "GOOGLE_CLIENT_ID":     settings.GOOGLE_CLIENT_ID,
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
    return await oauth.google.authorize_redirect(
        request,
        settings.GOOGLE_REDIRECT_URI
    )


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):

    # ── 1. Exchange code for Google token
    try:
        google_token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        logger.error(f"Google OAuth token exchange failed: {e}")
        raise HTTPException(status_code=400, detail="Google OAuth failed")

    google_user = google_token.get("userinfo")
    if not google_user:
        raise HTTPException(status_code=400, detail="Could not fetch user info from Google")

    email      = google_user.get("email")
    name       = google_user.get("name") or email
    avatar_url = google_user.get("picture")

    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email address")

    # ── 2. Check for existing user
    user       = db.query(AuthCredential).filter(AuthCredential.email == email).first()
    is_new     = False

    if user:
        # Conflict — registered with password, now trying Google
        if user.oauth_provider is None and user.hashed_password:
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists. Please log in with your password."
            )
        # Returning OAuth user — nothing to update in Auth (avatar lives in User Service)

    else:
        # ── 3. New user — create credentials first, then profile
        is_new = True
        user = AuthCredential(
            email=email,
            hashed_password=None,        # OAuth users have no password
            role=DBUserRole.buyer,       # default — can change after onboarding
            oauth_provider="google",
            is_active=True,
        )
        db.add(user)
        db.flush()   # assigns user.id without committing

        # ── 4. Create profile in User Service
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{settings.USER_SERVICE_URL}/users",
                    json={
                        "id":          str(user.id),
                        "email":       user.email,
                        "role":        user.role.value,
                        "full_name":   name,
                        "phone":       None,
                        "district":    None,
                        "avatar_url":  avatar_url,
                        "specialties": None,
                        "interests":   None,
                    },
                    headers={"x-internal-secret": settings.INTERNAL_SECRET},
                    timeout=5.0
                )
                res.raise_for_status()

            db.commit()
            db.refresh(user)

        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.error(f"User Service profile creation failed: {e}")
            db.rollback()   #keep auth and user DBs in sync
            raise HTTPException(
                status_code=503,
                detail="Could not create user profile. Please try again."
            )

    # ── 5. Issue our own tokens
    access_token  = create_access_token(str(user.id), user.role.value, user.email)
    refresh_token = create_refresh_token(str(user.id))

    # ── 6. Send tokens via HttpOnly cookies — never in URL query params
    redirect_url = (
        f"{settings.FRONTEND_URL}/auth/complete-profile"   # new user picks farmer/buyer
        if is_new else
        f"{settings.FRONTEND_URL}/marketplace"
    )
    response = RedirectResponse(url=redirect_url)

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,              # invisible to JavaScript
        secure=True,                # HTTPS only — set False in dev
        samesite="lax",
        max_age=60 * 60 * 24        # 24 hours
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30  # 30 days
    )
    return response