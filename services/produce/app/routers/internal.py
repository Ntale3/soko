import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config.dependencies import internal_only
from app.db.database import get_db
from app.models.produce import Listing, ListingStatus
from app.schemas.schemas import StockUpdatePayload

router = APIRouter(tags=["Internal"], dependencies=[Depends(internal_only)])


@router.put("/stock/decrement")
def decrement_stock(payload: StockUpdatePayload, db: Session = Depends(get_db)):
    """Called by Order Service when an order is confirmed."""
    listing = db.query(Listing).filter(Listing.id == uuid.UUID(payload.listing_id)).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.available_qty < payload.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")

    listing.available_qty -= payload.quantity
    if listing.available_qty <= 0:
        listing.available_qty = 0
        listing.status        = ListingStatus.sold_out

    db.commit()
    return {"available_qty": listing.available_qty, "status": listing.status.value}


@router.put("/stock/restore")
def restore_stock(payload: StockUpdatePayload, db: Session = Depends(get_db)):
    """Called by Order Service when an order is cancelled."""
    listing = db.query(Listing).filter(Listing.id == uuid.UUID(payload.listing_id)).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    listing.available_qty += payload.quantity
    if listing.status == ListingStatus.sold_out and listing.available_qty > 0:
        listing.status = ListingStatus.active

    db.commit()
    return {"available_qty": listing.available_qty, "status": listing.status.value}