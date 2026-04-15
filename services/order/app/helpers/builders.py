from app.models.order import Order, OrderItem
from app.schemas.order import (
    OrderOut, OrderItemOut, OrderSummaryOut,
    DeliveryAddress, PaymentMethod
)


def build_order_item_out(item: OrderItem) -> OrderItemOut:
    return OrderItemOut(
        cartItemId=str(item.id),
        productId=str(item.product_id),
        name=item.product_name,
        image=item.product_image or "",
        farmer=item.farmer_name,
        district="",          # not stored on item — farmerDetail covers this
        verified=False,       # not stored on item — farmerDetail covers this
        unit=item.unit,
        category=item.category,
        unitPrice=item.unit_price,
        quantity=item.quantity,
        subtotal=item.subtotal,
        minimumOrder=1,       # snapshot not stored — frontend uses for display only
        availableQty=0,       # snapshot at order time — not live
        addedAt=item.created_at.isoformat(),
        isSelected=True,
    )


def build_order_out(order: Order) -> OrderOut:
    return OrderOut(
        id=str(order.id),
        status=order.status.value,
        items=[build_order_item_out(i) for i in order.items],
        deliveryAddress=DeliveryAddress(
            fullName=order.delivery_full_name,
            phone=order.delivery_phone,
            district=order.delivery_district,
            subCounty=order.delivery_sub_county,
            village=order.delivery_village,
            landmark=order.delivery_landmark,
        ),
        paymentMethod=PaymentMethod(
            type=order.payment_type,
            provider=order.payment_provider,
            phoneNumber=order.payment_phone,
            accountName=order.payment_account,
        ),
        subtotal=order.subtotal,
        deliveryFee=order.delivery_fee,
        total=order.total,
        currency=order.currency,
        createdAt=order.created_at.isoformat(),
        updatedAt=order.updated_at.isoformat(),
        estimatedDelivery=order.estimated_delivery.isoformat()
            if order.estimated_delivery else None,
    )


def build_order_summary(order: Order) -> OrderSummaryOut:
    first = order.items[0].product_name if order.items else None
    return OrderSummaryOut(
        id=str(order.id),
        status=order.status.value,
        total=order.total,
        currency=order.currency,
        itemCount=len(order.items),
        createdAt=order.created_at.isoformat(),
        updatedAt=order.updated_at.isoformat(),
        firstItem=first,
    )