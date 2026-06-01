import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.helpers.pesapal import get_transaction_status
from app.models.payment import Transaction, PaymentStatus
from app.routers.internal import confirm_order_with_service, fail_order_with_service

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Webhook"])

PESAPAL_COMPLETED = "COMPLETED"
PESAPAL_FAILED    = "FAILED"
PESAPAL_REVERSED  = "REVERSED"
PESAPAL_INVALID   = "INVALID"


@router.get("/pesapal/ipn")
async def pesapal_ipn(
    orderTrackingId:  str = Query(...),
    orderMerchantRef: str = Query(...),
    orderNotifyType:  str = Query(...),
    db: Session = Depends(get_db)
):
    logger.info(f"IPN received: tracking_id={orderTrackingId} ref={orderMerchantRef}")

    tx = db.query(Transaction).filter(
        Transaction.pesapal_order_tracking_id == orderTrackingId
    ).first()

    if not tx:
        logger.warning(f"IPN for unknown tracking id: {orderTrackingId}")
        return {"status": "ok", "message": "Transaction not found"}

    if tx.status in (PaymentStatus.completed, PaymentStatus.failed, PaymentStatus.refunded):
        return {"status": "ok", "message": "Already processed"}

    try:
        status_data = await get_transaction_status(orderTrackingId)
    except Exception as e:
        logger.error(f"PesaPal status check failed: {e}")
        raise HTTPException(status_code=502, detail="Could not verify payment status")

    pesapal_status = status_data.get("payment_status_description", "").upper()
    payment_method = status_data.get("payment_method")

    logger.info(f"PesaPal status for {orderTrackingId}: {pesapal_status}")

    if pesapal_status == PESAPAL_COMPLETED:
        tx.status                 = PaymentStatus.completed
        tx.paid_at                = datetime.utcnow()
        tx.pesapal_payment_method = payment_method
        db.commit()

        await confirm_order_with_service(
            order_id=str(tx.order_id),
            transaction_id=str(tx.id),
            payment_reference=orderTrackingId,
        )

    elif pesapal_status in (PESAPAL_FAILED, PESAPAL_INVALID):
        tx.status         = PaymentStatus.failed
        tx.failure_reason = pesapal_status
        db.commit()

        await fail_order_with_service(
            order_id=str(tx.order_id),
            reason=f"PesaPal status: {pesapal_status}"
        )

    elif pesapal_status == PESAPAL_REVERSED:
        tx.status         = PaymentStatus.refunded
        tx.failure_reason = "Payment reversed by PesaPal"
        db.commit()

        await fail_order_with_service(
            order_id=str(tx.order_id),
            reason="Payment reversed"
        )

    else:
        logger.info(f"Payment still pending for order {tx.order_id}")

    return {"status": "ok", "orderNotificationType": orderNotifyType}


@router.get("/pesapal/callback")
async def pesapal_callback(
    order_id:        str = Query(...),
    OrderTrackingId: str = Query(...),
    db: Session = Depends(get_db)
):
    base = f"{settings.FRONTEND_URL}/checkout/confirmation"

    try:
        order_uuid = uuid.UUID(order_id)
    except ValueError:
        return RedirectResponse(f"{base}?orderId={order_id}&status=error")

    tx = db.query(Transaction).filter(
        Transaction.order_id == order_uuid
    ).first()

    if not tx:
        return RedirectResponse(f"{base}?orderId={order_id}&status=error")

    try:
        status_data    = await get_transaction_status(OrderTrackingId)
        pesapal_status = status_data.get("payment_status_description", "").upper()
    except Exception:
        return RedirectResponse(f"{base}?orderId={order_id}&status=error")

    if pesapal_status == PESAPAL_COMPLETED:
        return RedirectResponse(f"{base}?orderId={order_id}&status=success")
    elif pesapal_status in (PESAPAL_FAILED, PESAPAL_INVALID, PESAPAL_REVERSED):
        return RedirectResponse(f"{base}?orderId={order_id}&status=error")
    else:
        return RedirectResponse(f"{base}?orderId={order_id}&status=pending")