import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime,
    Float, Integer, Text, ForeignKey, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.database import Base
import enum


class OrderStatus(str, enum.Enum):
    pending    = "pending"
    confirmed  = "confirmed"
    processing = "processing"
    dispatched = "dispatched"
    delivered  = "delivered"
    cancelled  = "cancelled"


class PaymentMethodType(str, enum.Enum):
    mobile_money      = "mobile_money"
    cash_on_delivery  = "cash_on_delivery"
    bank_transfer     = "bank_transfer"


class Order(Base):
    __tablename__ = "orders"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buyer_id           = Column(UUID(as_uuid=True), nullable=False, index=True)
    status             = Column(SAEnum(OrderStatus), default=OrderStatus.pending, nullable=False)

    # Financials
    subtotal           = Column(Float, nullable=False)
    delivery_fee       = Column(Float, default=0.0)
    total              = Column(Float, nullable=False)
    currency           = Column(String, default="UGX")

    # Delivery address snapshot
    delivery_full_name = Column(String, nullable=False)
    delivery_phone     = Column(String, nullable=False)
    delivery_district  = Column(String, nullable=False)
    delivery_sub_county = Column(String, nullable=True)
    delivery_village   = Column(String, nullable=True)
    delivery_landmark  = Column(String, nullable=True)

    # Payment method snapshot
    payment_type       = Column(SAEnum(PaymentMethodType), nullable=False)
    payment_provider   = Column(String, nullable=True)    # "MTN" | "Airtel"
    payment_phone      = Column(String, nullable=True)
    payment_account    = Column(String, nullable=True)

    # Payment tracking
    payment_reference  = Column(String, nullable=True)    # PesaPal order tracking id
    paid_at            = Column(DateTime, nullable=True)

    estimated_delivery = Column(DateTime, nullable=True)

    created_at         = Column(DateTime, default=datetime.utcnow)
    updated_at         = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relations
    items = relationship("OrderItem", back_populates="order",
                         cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id    = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)

    # Snapshot of product at time of order — never reference live listing
    product_id  = Column(UUID(as_uuid=True), nullable=False)
    product_name = Column(String, nullable=False)
    product_image = Column(String, nullable=True)
    farmer_id   = Column(UUID(as_uuid=True), nullable=False)
    farmer_name = Column(String, nullable=False)
    unit        = Column(String, nullable=False)
    category    = Column(String, nullable=False)

    # Pricing snapshot
    unit_price  = Column(Float, nullable=False)
    quantity    = Column(Float, nullable=False)
    subtotal    = Column(Float, nullable=False)

    created_at  = Column(DateTime, default=datetime.utcnow)

    order = relationship("Order", back_populates="items")