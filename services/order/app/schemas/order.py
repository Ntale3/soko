from pydantic import BaseModel, field_validator
from typing import List, Optional
from enum import Enum


class OrderStatus(str, Enum):
    pending    = "pending"
    confirmed  = "confirmed"
    processing = "processing"
    dispatched = "dispatched"
    delivered  = "delivered"
    cancelled  = "cancelled"


class PaymentMethodType(str, Enum):
    mobile_money     = "mobile_money"
    cash_on_delivery = "cash_on_delivery"
    bank_transfer    = "bank_transfer"


# ── Matches DeliveryAddress in frontend
class DeliveryAddress(BaseModel):
    fullName:   str
    phone:      str
    district:   str
    subCounty:  Optional[str] = None
    village:    Optional[str] = None
    landmark:   Optional[str] = None


# ── Matches PaymentMethod in frontend
class PaymentMethod(BaseModel):
    type:          PaymentMethodType
    provider:      Optional[str] = None    # "MTN" | "Airtel"
    phoneNumber:   Optional[str] = None
    accountName:   Optional[str] = None

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v, info):
        if info.data.get("type") == "mobile_money" and not v:
            raise ValueError("provider required for mobile_money")
        return v

    @field_validator("phoneNumber")
    @classmethod
    def validate_phone(cls, v, info):
        if info.data.get("type") == "mobile_money" and not v:
            raise ValueError("phoneNumber required for mobile_money")
        return v


# ── Matches CheckoutPayload in frontend exactly
class CheckoutItem(BaseModel):
    productId:  str
    quantity:   float
    unitPrice:  float
    subtotal:   float


class CheckoutPayload(BaseModel):
    items:           List[CheckoutItem]
    deliveryAddress: DeliveryAddress
    paymentMethod:   PaymentMethod
    totalAmount:     float
    currency:        str = "UGX"

    @field_validator("items")
    @classmethod
    def must_have_items(cls, v):
        if not v:
            raise ValueError("Order must have at least one item")
        return v


# ── Matches CartItem in frontend — used in OrderOut
class OrderItemOut(BaseModel):
    cartItemId:   str       # order_item id — frontend CartItem.cartItemId
    productId:    str
    name:         str
    image:        str
    farmer:       str
    district:     str
    verified:     bool
    unit:         str
    category:     str
    unitPrice:    float
    quantity:     float
    subtotal:     float
    minimumOrder: float
    availableQty: float
    addedAt:      str
    isSelected:   bool = True


# ── Matches Order in frontend exactly
class OrderOut(BaseModel):
    id:                str
    status:            str
    items:             List[OrderItemOut]
    deliveryAddress:   DeliveryAddress
    paymentMethod:     PaymentMethod
    subtotal:          float
    deliveryFee:       float
    total:             float
    currency:          str
    createdAt:         str
    updatedAt:         str
    estimatedDelivery: Optional[str] = None


# ── Order summary for history list (lighter than full OrderOut)
class OrderSummaryOut(BaseModel):
    id:          str
    status:      str
    total:       float
    currency:    str
    itemCount:   int
    createdAt:   str
    updatedAt:   str
    firstItem:   Optional[str] = None   # name of first product — for list display


# ── Internal — Payment Service calls this to confirm payment
class PaymentConfirmPayload(BaseModel):
    order_id:          str
    payment_reference: str
    paid_at:           str   # ISO


# ── Internal — Payment Service calls this to mark payment failed
class PaymentFailedPayload(BaseModel):
    order_id: str
    reason:   str


# ── Status update — admin or farmer can update order status
class UpdateOrderStatusPayload(BaseModel):
    status: OrderStatus