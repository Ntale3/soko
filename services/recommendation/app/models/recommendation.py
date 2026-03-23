from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.sql import func
from app.database import Base


class OrderEvent(Base):
    """Persisted copy of every order.placed event from the Buyer service."""
    __tablename__ = "order_events"

    id         = Column(Integer, primary_key=True, index=True)
    order_id   = Column(Integer, nullable=False, unique=True, index=True)
    buyer_id   = Column(Integer, nullable=False, index=True)
    produce_id = Column(Integer, nullable=False, index=True)
    farmer_id  = Column(Integer, nullable=False)
    quantity_kg  = Column(Float, nullable=False)
    total_price  = Column(Float, nullable=False)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())


class QualityScore(Base):
    """Persisted copy of every quality.scored event from the Buyer service."""
    __tablename__ = "quality_scores"

    id         = Column(Integer, primary_key=True, index=True)
    produce_id = Column(Integer, nullable=False, index=True)
    farmer_id  = Column(Integer, nullable=False, index=True)
    buyer_id   = Column(Integer, nullable=False)
    stars      = Column(Integer, nullable=False)  # 1–5
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProduceSummary(Base):
    """Lightweight catalogue entry synced from produce.listed events."""
    __tablename__ = "produce_summaries"

    id             = Column(Integer, primary_key=True, index=True)
    produce_id     = Column(Integer, nullable=False, unique=True, index=True)
    farmer_id      = Column(Integer, nullable=False)
    name           = Column(String, nullable=False)
    category       = Column(String, nullable=False)
    district       = Column(String, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    unit           = Column(String, nullable=False)
    last_updated   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
