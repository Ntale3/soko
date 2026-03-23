from pydantic import BaseModel
from datetime import datetime


# ── Farm schemas ─────────────────────────────────────────────────────
class FarmCreate(BaseModel):
    name: str
    location: str
    size_acres: float | None = None


class FarmOut(BaseModel):
    id: int
    name: str
    location: str
    size_acres: float | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Farmer Profile schemas ────────────────────────────────────────────
class FarmerProfileCreate(BaseModel):
    full_name: str
    phone: str | None = None
    district: str | None = None


class FarmerProfileUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    district: str | None = None


class FarmerProfileOut(BaseModel):
    id: int
    user_id: int
    full_name: str
    phone: str | None
    district: str | None
    is_verified: bool
    created_at: datetime
    farms: list[FarmOut] = []

    model_config = {"from_attributes": True}


class FarmerListOut(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[FarmerProfileOut]
