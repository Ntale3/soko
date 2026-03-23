from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.order import Order, OrderStatus
from app.schemas import OrderOut, OrderListOut
from app.dependencies import require_farmer
from app.messaging import publish_event

router = APIRouter(prefix="/farmer/orders", tags=["Farmer Orders"])

# Valid farmer-driven status transitions
_ALLOWED: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.pending:   {OrderStatus.confirmed, OrderStatus.rejected},
    OrderStatus.confirmed: {OrderStatus.completed},
}


@router.get("/", response_model=OrderListOut)
def list_farmer_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    status: OrderStatus | None = Query(default=None),
    db: Session = Depends(get_db),
    user_id: int = Depends(require_farmer),
):
    """List all orders placed against this farmer's produce."""
    query = db.query(Order).filter(Order.farmer_id == user_id)
    if status:
        query = query.filter(Order.status == status)

    total = query.count()
    orders = (
        query.order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"total": total, "page": page, "page_size": page_size, "results": orders}


@router.get("/{order_id}", response_model=OrderOut)
def get_farmer_order(
    order_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_farmer),
):
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.farmer_id == user_id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}/status", response_model=OrderOut)
async def update_order_status(
    order_id: int,
    new_status: OrderStatus,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_farmer),
):
    """
    Farmer-driven status transitions:
      pending   → confirmed | rejected
      confirmed → completed
    """
    order = db.query(Order).filter(
        Order.id == order_id,
        Order.farmer_id == user_id,
    ).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    allowed = _ALLOWED.get(order.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot move order from '{order.status}' to '{new_status}'",
        )

    order.status = new_status
    db.commit()
    db.refresh(order)

    if new_status == OrderStatus.completed:
        await publish_event("order.completed", {
            "order_id": order.id,
            "produce_id": order.produce_id,
            "farmer_id": order.farmer_id,
            "quantity_kg": order.quantity_kg,
            "total_price": order.total_price,
        })

    return order
