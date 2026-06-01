from pydantic import BaseModel
from typing import Optional
from enum import Enum


class PaymentStatus(str, Enum):
    pending   = "pending"
    completed = "completed"
    failed    = "failed"
    cancelled = "cancelled"
    refunded  = "refunded"


class PaymentMethodType(str, Enum):
    pesapal          = "pesapal"
    mobile_money     = "mobile_money"
    cash_on_delivery = "cash_on_delivery"
    bank_transfer    = "bank_transfer"


# ── Payment method snapshot passed from Order Service
class PaymentMethodPayload(BaseModel):
    type:        PaymentMethodType
    provider:    Optional[str] = None
    phoneNumber: Optional[str] = None
    accountName: Optional[str] = None


# ── Internal — Order Service calls this to initiate payment
class InitiatePaymentPayload(BaseModel):
    order_id:       str
    buyer_id:       str
    amount:         float
    currency:       str = "UGX"
    payment_method: PaymentMethodPayload
    description:    str


# ── Response back to Order Service after initiation
class InitiatePaymentResponse(BaseModel):
    transaction_id: str
    payment_url:    Optional[str]   # PesaPal redirect URL
    status:         PaymentStatus
    message:        str


# ── Transaction out — buyer's payment history
class TransactionOut(BaseModel):
    id:             str
    orderId:        str
    amount:         float
    currency:       str
    status:         str
    paymentMethod:  str
    paidAt:         Optional[str]
    createdAt:      str


# ── PesaPal IPN payload (what PesaPal POSTs to your webhook)
class PesaPalIPNPayload(BaseModel):
    orderTrackingId:  str
    orderMerchantRef: str
    orderNotifyType:  str


# ── PesaPal token response
class PesaPalTokenResponse(BaseModel):
    token:   str
    expiry:  str