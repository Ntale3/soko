from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class FarmerProfile(Base):
    """
    One-to-one with Auth service User (linked by user_id).
    A farmer registers in Auth first, then creates their profile here.
    """
    __tablename__ = "farmer_profiles"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, unique=True, nullable=False, index=True)  # FK to auth_db
    full_name   = Column(String, nullable=False)
    phone       = Column(String, nullable=True)
    district    = Column(String, nullable=True)   # e.g. Kampala, Wakiso, Mbale
    is_verified = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), onupdate=func.now())

    farms = relationship("Farm", back_populates="farmer", cascade="all, delete-orphan")


class Farm(Base):
    """
    A farmer can have multiple farms/plots.
    """
    __tablename__ = "farms"

    id          = Column(Integer, primary_key=True, index=True)
    farmer_id   = Column(Integer, ForeignKey("farmer_profiles.id"), nullable=False)
    name        = Column(String, nullable=False)        # e.g. "Mukono Plot"
    location    = Column(String, nullable=False)        # e.g. "Mukono, Central Uganda"
    size_acres  = Column(Float, nullable=True)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    farmer = relationship("FarmerProfile", back_populates="farms")
