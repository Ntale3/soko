from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Union
from app.db.session import get_db
from app.models.user import User, UserRole as DBUserRole
from app.schemas.auth import (
    FarmerRegisterPayload, BuyerRegisterPayload,
    LoginPayload, AuthTokens, AuthenticatedUser, LoginResponse
)
from app.core.security import hash_password, verify_password, create_access_token
from app.core.dependencies import get_current_user

router = APIRouter(tags=["Auth"])


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


@router.post("/register", response_model=LoginResponse, status_code=201)
def register(
    payload: Union[FarmerRegisterPayload, BuyerRegisterPayload],
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    if db.query(User).filter(User.phone == payload.phone).first():
        raise HTTPException(status_code=409, detail="Phone already registered")

    specialties = None
    if hasattr(payload, "specialties") and payload.specialties:
        specialties = ",".join(payload.specialties)

    user = User(
        full_name=payload.fullName,
        email=payload.email,
        phone=payload.phone,
        hashed_password=hash_password(payload.password),
        district=payload.district,
        role=DBUserRole(payload.role),
        specialties=specialties,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id), user.role.value, user.email, user.full_name)
    return LoginResponse(tokens=AuthTokens(access_token=token), user=user_to_schema(user))


@router.post("/login", response_model=LoginResponse, status_code=200)
def login(payload: LoginPayload, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(str(user.id), user.role.value, user.email, user.full_name)
    return LoginResponse(tokens=AuthTokens(access_token=token), user=user_to_schema(user))


@router.get("/me", response_model=AuthenticatedUser)
def get_me(current_user: User = Depends(get_current_user)):
    return user_to_schema(current_user)


@router.post("/refresh")
def refresh_token(current_user: User = Depends(get_current_user)):
    token = create_access_token(str(current_user.id), current_user.role.value, current_user.email, current_user.full_name)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/health")
def health():
    return {"status": "ok", "service": "auth"}