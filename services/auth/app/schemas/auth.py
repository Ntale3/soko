from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Literal, List
from enum import Enum

class UserRole(str, Enum):
    buyer = "buyer"
    farmer = "farmer"
    both = "both"

class VerificationStatus(str, Enum):
    unverified = "unverified"
    pending = "pending"
    verified = "verified"
    rejected = "rejected"

# ── Register
class BaseRegisterPayload(BaseModel):
    fullName: str
    email: EmailStr
    password: str
    phone: str
    district: str
    role: UserRole

    @field_validator("password")
    @classmethod
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

class FarmerRegisterPayload(BaseRegisterPayload):
    role: Literal[UserRole.farmer, UserRole.both]
    specialties: List[str] = []

    @field_validator("specialties")
    @classmethod
    def max_specialties(cls, v):
        if len(v) > 3:
            raise ValueError("Maximum 3 specialties allowed")
        return v

class BuyerRegisterPayload(BaseRegisterPayload):
    role: Literal[UserRole.buyer]

# ── Login
class LoginPayload(BaseModel):
    email: EmailStr
    password: str

# ── Token
class AuthTokens(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: str | None = None
    role: UserRole | None = None

# ── Authenticated user response (matches your TS AuthenticatedUser type)
class AuthenticatedUser(BaseModel):
    id: str
    name: str
    initials: str
    email: str
    phone: str
    avatarUrl: Optional[str] = None
    district: str
    village: Optional[str] = None
    role: UserRole
    verified: bool
    verificationStatus: VerificationStatus
    memberSince: str
    farmerBio: Optional[str] = None
    farmName: Optional[str] = None

class LoginResponse(BaseModel):
    tokens: AuthTokens
    user: AuthenticatedUser

# ── Profile update
class UpdateProfile(BaseModel):
    fullName: Optional[str] = None
    phone: Optional[str] = None
    district: Optional[str] = None
    village: Optional[str] = None
    farmerBio: Optional[str] = None
    farmName: Optional[str] = None
    avatarUrl: Optional[str] = None

# ── Settings update
class UpdateSettings(BaseModel):
    notificationsEmail: Optional[bool] = None
    notificationsSms: Optional[bool] = None
    notificationsPush: Optional[bool] = None
