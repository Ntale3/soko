from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from app.database import Base
import enum


class ProduceUnit(str, enum.Enum):
    kg    = "kg"
    unit  = "unit"
    bunch = "bunch"


class ProduceCategory(str, enum.Enum):
    vegetables  = "vegetables"
    grains      = "grains"
    fruits      = "fruits"
    cash_crops  = "cash_crops"
    dairy       = "dairy"
    herbs       = "herbs"
    livestock   = "livestock"
    other       = "other"


class ProduceListing(Base):
    __tablename__ = "produce_listings"

    id             = Column(Integer, primary_key=True, index=True)
    farmer_id      = Column(Integer, nullable=False, index=True)  # FK to farmer_db
    user_id        = Column(Integer, nullable=False, index=True)  # FK to auth_db, for quick auth checks
    farmer_name    = Column(String, nullable=True)                # denormalised for fast reads
    name           = Column(String, nullable=False, index=True)
    description    = Column(String, nullable=True)
    category       = Column(Enum(ProduceCategory, native_enum=False), nullable=False)
    unit           = Column(Enum(ProduceUnit, native_enum=False), default=ProduceUnit.kg, nullable=False)
    quantity       = Column(Float, nullable=False)               # available stock
    price_per_unit = Column(Float, nullable=False)
    district       = Column(String, nullable=False, index=True)  # indexed for fast district search
    is_available   = Column(Boolean, default=True, nullable=False)
    avg_rating     = Column(Float, default=0.0, nullable=False)
    review_count   = Column(Integer, default=0, nullable=False)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())
