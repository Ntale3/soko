from pydantic import BaseModel, field_validator
from datetime import datetime
from app.models.produce import ProduceUnit, ProduceCategory


# ── Create ────────────────────────────────────────────────────────────
class ProduceListingCreate(BaseModel):
    name: str
    description: str | None = None
    category: ProduceCategory
    unit: ProduceUnit = ProduceUnit.kg
    quantity: float
    price_per_unit: float
    district: str

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v

    @field_validator("price_per_unit")
    @classmethod
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Price must be greater than 0")
        return v


# ── Update — all fields optional ─────────────────────────────────────
class ProduceListingUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: ProduceCategory | None = None
    unit: ProduceUnit | None = None
    quantity: float | None = None
    price_per_unit: float | None = None
    district: str | None = None
    is_available: bool | None = None


# ── Response ──────────────────────────────────────────────────────────
class ProduceListingOut(BaseModel):
    id: int
    farmer_id: int
    farmer_name: str | None
    name: str
    description: str | None
    category: ProduceCategory
    unit: ProduceUnit
    quantity: float
    price_per_unit: float
    district: str
    is_available: bool
    avg_rating: float
    review_count: int
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


# ── Paginated list response ───────────────────────────────────────────
class ProduceListOut(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[ProduceListingOut]
