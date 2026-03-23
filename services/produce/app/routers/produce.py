import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.database import get_db
from app.models.produce import ProduceListing, ProduceCategory
from app.schemas import ProduceListingCreate, ProduceListingUpdate, ProduceListingOut, ProduceListOut
from app.dependencies import require_farmer
from app.messaging import publish_event
from app.config import settings

router = APIRouter(prefix="/produce", tags=["Produce"])


async def _fetch_farmer_name(user_id: int) -> str | None:
    """Look up the farmer's display name from the farmer service."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.FARMER_SERVICE_URL}/farmers/by-user/{user_id}")
            if resp.status_code == 200:
                return resp.json().get("full_name")
    except Exception:
        pass
    return None


# ── GET /produce/prices/predictions — stub for frontend price cards ───
@router.get("/prices/predictions", tags=["Produce"])
def get_price_predictions(
    category: ProduceCategory | None = Query(default=None),
    district: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """
    Returns average price per category (and optionally district) derived
    from active listings. The frontend uses this for price prediction cards.
    """
    query = db.query(ProduceListing).filter(ProduceListing.is_available == True)
    if category:
        query = query.filter(ProduceListing.category == category)
    if district:
        query = query.filter(ProduceListing.district.ilike(f"%{district}%"))

    listings = query.all()

    # Group by category and compute averages
    from collections import defaultdict
    buckets: dict = defaultdict(list)
    for l in listings:
        buckets[l.category].append(l.price_per_unit)

    results = [
        {
            "category": cat,
            "avg_price_per_kg": round(sum(prices) / len(prices), 2),
            "listing_count": len(prices),
        }
        for cat, prices in buckets.items()
    ]
    return {"results": results}


# ── POST /produce — create listing (farmer only) ──────────────────────
@router.post("/", response_model=ProduceListingOut, status_code=status.HTTP_201_CREATED)
async def create_listing(
    payload: ProduceListingCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_farmer)
):
    farmer_name = await _fetch_farmer_name(user_id)

    listing = ProduceListing(
        farmer_id=user_id,
        user_id=user_id,
        farmer_name=farmer_name,
        **payload.model_dump()
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)

    await publish_event("produce.listed", {
        "produce_id": listing.id,
        "farmer_id": listing.farmer_id,
        "name": listing.name,
        "category": listing.category,
        "district": listing.district,
        "price_per_unit": listing.price_per_unit,
        "unit": listing.unit,
    })

    return listing


# ── GET /produce — search and browse listings (public) ────────────────
@router.get("/", response_model=ProduceListOut)
def get_listings(
    name: str | None = Query(default=None, description="Search by name"),
    district: str | None = Query(default=None, description="Filter by district"),
    category: ProduceCategory | None = Query(default=None),
    min_price: float | None = Query(default=None),
    max_price: float | None = Query(default=None),
    available_only: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    query = db.query(ProduceListing)

    if available_only:
        query = query.filter(ProduceListing.is_available == True)
    if name:
        query = query.filter(ProduceListing.name.ilike(f"%{name}%"))
    if district:
        query = query.filter(ProduceListing.district.ilike(f"%{district}%"))
    if category:
        query = query.filter(ProduceListing.category == category)
    if min_price is not None:
        query = query.filter(ProduceListing.price_per_unit >= min_price)
    if max_price is not None:
        query = query.filter(ProduceListing.price_per_unit <= max_price)

    total = query.count()
    listings = query.order_by(ProduceListing.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return {"total": total, "page": page, "page_size": page_size, "results": listings}


# ── GET /produce/farmer/mine — farmer's own listings ──────────────────
@router.get("/farmer/mine", response_model=ProduceListOut)
def get_my_listings(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    user_id: int = Depends(require_farmer)
):
    query = db.query(ProduceListing).filter(ProduceListing.user_id == user_id)
    total = query.count()
    listings = query.order_by(ProduceListing.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return {"total": total, "page": page, "page_size": page_size, "results": listings}


# ── GET /produce/{id} — single listing (public) ───────────────────────
@router.get("/{produce_id}", response_model=ProduceListingOut)
def get_listing(produce_id: int, db: Session = Depends(get_db)):
    listing = db.query(ProduceListing).filter(ProduceListing.id == produce_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


# ── PATCH /produce/{id} — update listing (farmer only) ───────────────
@router.patch("/{produce_id}", response_model=ProduceListingOut)
def update_listing(
    produce_id: int,
    payload: ProduceListingUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_farmer)
):
    listing = db.query(ProduceListing).filter(
        ProduceListing.id == produce_id,
        ProduceListing.user_id == user_id
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found or not yours")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(listing, field, value)

    db.commit()
    db.refresh(listing)
    return listing


# ── DELETE /produce/{id} — delete listing (farmer only) ──────────────
@router.delete("/{produce_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(
    produce_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(require_farmer)
):
    listing = db.query(ProduceListing).filter(
        ProduceListing.id == produce_id,
        ProduceListing.user_id == user_id
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found or not yours")

    db.delete(listing)
    db.commit()


# ── PATCH /produce/{id}/reduce-stock — called by Buyer service ────────
class StockReduction(BaseModel):
    quantity: float


@router.patch("/{produce_id}/reduce-stock", response_model=ProduceListingOut)
def reduce_stock(
    produce_id: int,
    payload: StockReduction,
    db: Session = Depends(get_db)
):
    """
    Called internally by Buyer service after a confirmed order.
    No JWT required — internal service-to-service call only.
    In production this would be secured via an internal API key.
    """
    listing = db.query(ProduceListing).filter(
        ProduceListing.id == produce_id
    ).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    listing.quantity = max(0, listing.quantity - payload.quantity)

    if listing.quantity <= 0:
        listing.is_available = False

    db.commit()
    db.refresh(listing)
    return listing
