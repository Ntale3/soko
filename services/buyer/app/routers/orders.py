from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.buyer import BuyerProfile
from app.models.order import Order, OrderStatus
from app.schemas import OrderCreate, OrderOut, OrderListOut
from app.dependencies import require_buyer
from app.http_client import get_produce_listing, reduce_produce_stock
from app.messaging import publish_event

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("/", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def place_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_buyer)
):
    # 1. Get buyer profile
    profile = db.query(BuyerProfile).filter(BuyerProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Create your buyer profile first")

    # 2. Verify produce exists and has enough stock via HTTP call to Produce service
    listing = await get_produce_listing(payload.produce_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Produce listing not found")
    if not listing.get("is_available"):
        raise HTTPException(status_code=400, detail="Produce is no longer available")
    if listing.get("quantity", 0) < payload.quantity_kg:
        raise HTTPException(
            status_code=400,
            detail=f"Only {listing['quantity']}kg available, you requested {payload.quantity_kg}kg"
        )

    # 3. Calculate total
    price_per_kg = listing["price_per_unit"]
    total_price = round(price_per_kg * payload.quantity_kg, 2)

    # 4. Reserve stock on Produce service BEFORE saving the order.
    #    If this fails nothing is committed — state stays clean.
    stock_reduced = await reduce_produce_stock(payload.produce_id, payload.quantity_kg)
    if not stock_reduced:
        raise HTTPException(
            status_code=503,
            detail="Could not reserve stock — produce service unavailable, please try again",
        )

    # 5. Save order only after stock is successfully reserved
    order = Order(
        buyer_id=profile.id,
        produce_id=payload.produce_id,
        farmer_id=listing["farmer_id"],
        quantity_kg=payload.quantity_kg,
        price_per_kg=price_per_kg,
        total_price=total_price,
        status=OrderStatus.pending,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    # 6. Publish event
    await publish_event("order.placed", {
        "order_id": order.id,
        "produce_id": order.produce_id,
        "farmer_id": order.farmer_id,
        "buyer_id": user_id,   # auth user_id — matches JWT sub used by recommendation service
        "quantity_kg": order.quantity_kg,
        "total_price": order.total_price,
    })

    return order


@router.get("/", response_model=OrderListOut)
def get_my_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    status: OrderStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    user_id: int = Depends(require_buyer)
):
    profile = db.query(BuyerProfile).filter(BuyerProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    query = db.query(Order).filter(Order.buyer_id == profile.id)
    if status:
        query = query.filter(Order.status == status)

    total = query.count()
    orders = query.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {"total": total, "page": page, "page_size": page_size, "results": orders}


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_buyer)
):
    profile = db.query(BuyerProfile).filter(BuyerProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    order = db.query(Order).filter(
        Order.id == order_id,
        Order.buyer_id == profile.id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_buyer)
):
    profile = db.query(BuyerProfile).filter(BuyerProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    order = db.query(Order).filter(
        Order.id == order_id,
        Order.buyer_id == profile.id
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Can only cancel a pending order
    if order.status != OrderStatus.pending:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel an order with status '{order.status}'"
        )

    order.status = OrderStatus.cancelled
    db.commit()
    db.refresh(order)
    return order
