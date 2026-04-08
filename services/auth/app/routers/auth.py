from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import AuthCredential, UserRole as DBUserRole
from app.core.config import settings
from app.schemas.auth import (
    RegisterPayload, LoginPayload, LoginResponse,
    AuthTokens, AuthUserMinimal,
    VerifyTokenRequest, VerifyTokenResponse,
    ChangePasswordPayload
)
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token
)
from app.core.dependencies import get_current_user
import httpx

router = APIRouter(tags=["Auth"])

USER_SERVICE_URL = settings.USER_SERVICE_URL


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(payload: RegisterPayload, db: Session = Depends(get_db)):
    if db.query(AuthCredential).filter(AuthCredential.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    cred = AuthCredential(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=DBUserRole(payload.role),
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)

    # Tell User Service to create a profile shell
    async with httpx.AsyncClient() as client:
        await client.post(f"{USER_SERVICE_URL}/users", json={
            "id": str(cred.id),
            "email": cred.email,
            "role": cred.role.value,
            "name": payload.fullName,
            "phone" : payload.phone,
            "district": payload.district,
            "specialties": payload.specialties,
            "intrests": payload.interests,
            "avatar_url": payload.avatar_url
        })

    access_token = create_access_token(str(cred.id), cred.role.value, cred.email)
    refresh_token = create_refresh_token(str(cred.id))

    return LoginResponse(
        tokens=AuthTokens(access_token=access_token, refresh_token=refresh_token),
        user=AuthUserMinimal(id=str(cred.id), email=cred.email, role=cred.role.value)
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginPayload, db: Session = Depends(get_db)):
    cred = db.query(AuthCredential).filter(AuthCredential.email == payload.email).first()
    if not cred or not verify_password(payload.password, cred.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not cred.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    access_token = create_access_token(str(cred.id), cred.role.value, cred.email)
    refresh_token = create_refresh_token(str(cred.id))

    return LoginResponse(
        tokens=AuthTokens(access_token=access_token, refresh_token=refresh_token),
        user=AuthUserMinimal(id=str(cred.id), email=cred.email, role=cred.role.value)
    )


@router.post("/verify-token", response_model=VerifyTokenResponse)
def verify_token(payload: VerifyTokenRequest):
    # This is called by the Gateway only — not the frontend
    data = decode_token(payload.token)
    if not data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return VerifyTokenResponse(
        valid=True,
        user_id=data["sub"],
        role=data["role"],
        email=data["email"]
    )


@router.post("/refresh", response_model=AuthTokens)
def refresh_token(payload: VerifyTokenRequest,db: Session = Depends(get_db)):
    data = decode_token(payload.token)
    if not data:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    # Fetch role from DB since refresh token doesn't carry it
    user = db.query(AuthCredential).filter(AuthCredential.id == data["sub"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="user not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="user account disabled")

    # (keep refresh tokens lean)
    return AuthTokens(
        access_token=create_access_token(user.id, user.role.value, user.email),
        refresh_token=create_refresh_token(user.id)
    )

@router.post("/change-password")
def change_password(
    payload: ChangePasswordPayload,
    current_user: AuthCredential = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password updated"}


@router.post("/refresh")
def refresh_token(current_user: User = Depends(get_current_user)):
    token = create_access_token(str(current_user.id), current_user.role.value, current_user.email, current_user.full_name)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/refresh")
def refresh_token(current_user: User = Depends(get_current_user)):
    token = create_access_token(str(current_user.id), current_user.role.value, current_user.email, current_user.full_name)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/health")
def health():
    return {"status": "ok", "service": "auth"}