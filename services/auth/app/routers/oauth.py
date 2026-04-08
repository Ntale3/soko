from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config as StarletteConfig
from app.db.session import get_db
from app.models.user import User, UserRole as DBUserRole, VerificationStatus
from app.schemas.auth import AuthTokens, AuthenticatedUser, LoginResponse
from app.core.security import create_access_token
from app.core.config import settings

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

def make_initials(name: str) -> str:
    parts = name.strip().split()
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else name[:2].upper()

def user_to_schema(user: User) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=str(user.id),
        name=user.full_name,
        initials=make_initials(user.full_name),
        email=user.email,
        phone=user.phone or "",
        avatarUrl=user.avatar_url,
        district=user.district or "",
        village=user.village,
        role=user.role.value,
        verified=user.verified,
        verificationStatus=user.verification_status.value,
        memberSince=user.created_at.isoformat(),
        farmerBio=user.farmer_bio,
        farmName=user.farm_name,
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
    user = db.query(User).filter(User.email == email).first()

    if not user:
        # New user via Google — we default role to buyer
        # They can update their role later in settings
        user = User(
            full_name=name,
            email=email,
            phone=None,
            password_hash="",
            district="",
            role=DBUserRole.buyer,
            avatar_url=avatar_url,
            verified=True,
            verification_status=VerificationStatus.verified,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    else:
        # Existing user — update their avatar if Google has one
        if avatar_url and not user.avatar_url:
            user.avatar_url = avatar_url
            db.commit()
            db.refresh(user)

    token = create_access_token(
        str(user.id), user.role.value, user.email, user.full_name
    )

    # In production redirect to frontend with token in query param or cookie
    # For now return JSON same as normal login
    # return LoginResponse(
    #     tokens=AuthTokens(access_token=token),
    #     user=user_to_schema(user)
    # )
    frontend_url = f"{settings.FRONTEND_URL}/auth/google/callback?access_token={token}&redirect=/marketplace"
    return RedirectResponse(url=frontend_url)