import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime,
    Float, Text, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from app.db.database import Base
import enum


class PaymentStatus(str, enum.Enum):
    pending   = "pending"
    completed = "completed"
    failed    = "failed"
    cancelled = "cancelled"
    refunded  = "refunded"


class PaymentMethodType(str, enum.Enum):
    pesapal          = "pesapal"
    mobile_money     = "mobile_money"
    cash_on_delivery = "cash_on_delivery"
    bank_transfer    = "bank_transfer"


class Transaction(Base):
    __tablename__ = "transactions"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id            = Column(UUID(as_uuid=True), nullable=False, index=True, unique=True)
    buyer_id            = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Financials
    amount              = Column(Float,  nullable=False)
    currency            = Column(String, default="UGX")

    # Payment method
    payment_method_type = Column(SAEnum(PaymentMethodType), nullable=False)
    payment_provider    = Column(String, nullable=True)    # MTN | Airtel
    payment_phone       = Column(String, nullable=True)

    # Status
    status              = Column(SAEnum(PaymentStatus), default=PaymentStatus.pending)
    failure_reason      = Column(Text,   nullable=True)

    # PesaPal tracking
    pesapal_order_tracking_id = Column(String, nullable=True, index=True)
    pesapal_merchant_ref      = Column(String, nullable=True)
    pesapal_payment_url       = Column(String, nullable=True)
    pesapal_payment_method    = Column(String, nullable=True)  # what PesaPal reports

    # IPN registration
    pesapal_ipn_id      = Column(String, nullable=True)

    paid_at             = Column(DateTime, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)