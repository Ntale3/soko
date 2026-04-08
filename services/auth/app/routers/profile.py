from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AuthenticatedUser, UpdateProfile, UpdateSettings
from app.core.dependencies import get_current_user

router = APIRouter(tags=["Profile"])

def make_initials(name: str) -> str:
    parts = name.strip().split()
    return (parts[0][0] + parts[-1][0]).upper() if len(parts) >= 2 else name[:2].upper()

def user_to_schema(user: User) -> AuthenticatedUser:
    return AuthenticatedUser(
        id=str(user.id),
        name=user.full_name,
        initials=make_initials(user.full_name),
        email=user.email,
        phone=user.phone,
        avatarUrl=user.avatar_url,
        district=user.district,
        village=user.village,
        role=user.role.value,
        verified=user.verified,
        verificationStatus=user.verification_status.value,
        memberSince=user.created_at.isoformat(),
        farmerBio=user.farmer_bio,
        farmName=user.farm_name,
    )

@router.patch("/me", response_model=AuthenticatedUser)
def update_profile(
    payload: UpdateProfile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if payload.fullName is not None:
        current_user.full_name = payload.fullName
    if payload.phone is not None:
        if db.query(User).filter(User.phone == payload.phone, User.id != current_user.id).first():
            raise HTTPException(status_code=409, detail="Phone already in use")
        current_user.phone = payload.phone
    if payload.district is not None:
        current_user.district = payload.district
    if payload.village is not None:
        current_user.village = payload.village
    if payload.farmerBio is not None:
        current_user.farmer_bio = payload.farmerBio
    if payload.farmName is not None:
        current_user.farm_name = payload.farmName
    if payload.avatarUrl is not None:
        current_user.avatar_url = payload.avatarUrl

    db.commit()
    db.refresh(current_user)
    return user_to_schema(current_user)

@router.patch("/me/settings", response_model=AuthenticatedUser)
def update_settings(
    payload: UpdateSettings,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if payload.notificationsEmail is not None:
        current_user.notifications_email = payload.notificationsEmail
    if payload.notificationsSms is not None:
        current_user.notifications_sms = payload.notificationsSms
    if payload.notificationsPush is not None:
        current_user.notifications_push = payload.notificationsPush


    db.commit()
    db.refresh(current_user)
    return user_to_schema(current_user)