from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import jwt, JWTError

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database import get_db
from app.models.recommendation import OrderEvent, QualityScore, ProduceSummary
from app.schemas import RecommendationItem, RecommendationListOut, ProduceScoreOut
from app.config import settings

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
bearer = HTTPBearer()


def _get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> int:
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return int(user_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def _avg_stars(produce_id: int, db: Session) -> float | None:
    result = db.query(func.avg(QualityScore.stars)).filter(
        QualityScore.produce_id == produce_id
    ).scalar()
    return round(float(result), 2) if result is not None else None


@router.get("/", response_model=RecommendationListOut)
def get_recommendations(
    limit: int = 10,
    db: Session = Depends(get_db),
    user_id: int = Depends(_get_current_user_id),
):
    """
    Returns personalised produce recommendations for the authenticated buyer.

    Scoring logic:
    - +0.4 if the produce is in a category the buyer has ordered before
    - +0.3 if it's in a district the buyer has ordered from
    - +0.3 based on normalised average star rating (if any reviews exist)
    Produce the buyer has already ordered is excluded.
    """
    # Buyer's historical categories and districts
    buyer_orders = db.query(OrderEvent).filter(OrderEvent.buyer_id == user_id).all()
    ordered_produce_ids = {o.produce_id for o in buyer_orders}
    buyer_categories = {o.produce_id for o in buyer_orders}  # resolved below via summaries

    # Resolve categories/districts from produce summaries
    if ordered_produce_ids:
        past_summaries = db.query(ProduceSummary).filter(
            ProduceSummary.produce_id.in_(ordered_produce_ids)
        ).all()
        preferred_categories = {s.category for s in past_summaries}
        preferred_districts  = {s.district  for s in past_summaries}
    else:
        preferred_categories = set()
        preferred_districts  = set()

    # Candidate produce — exclude already ordered
    candidates = db.query(ProduceSummary).filter(
        ProduceSummary.produce_id.notin_(ordered_produce_ids)
    ).all() if ordered_produce_ids else db.query(ProduceSummary).all()

    # Build recommendation list with scores
    items: list[RecommendationItem] = []
    for p in candidates:
        score = 0.0
        reasons = []

        if preferred_categories and p.category in preferred_categories:
            score += 0.4
            reasons.append(f"matches your preferred category ({p.category})")

        if preferred_districts and p.district in preferred_districts:
            score += 0.3
            reasons.append(f"available in your area ({p.district})")

        avg = _avg_stars(p.produce_id, db)
        if avg is not None:
            score += round((avg / 5.0) * 0.3, 4)
            reasons.append(f"rated {avg}/5 by buyers")

        if not reasons:
            reasons.append("available on the market")

        items.append(RecommendationItem(
            produce_id=p.produce_id,
            farmer_id=p.farmer_id,
            name=p.name,
            category=p.category,
            district=p.district,
            price_per_unit=p.price_per_unit,
            unit=p.unit,
            avg_stars=avg,
            score=round(score, 4),
            reason=", ".join(reasons),
        ))

    # Sort by score descending, take top N
    items.sort(key=lambda x: x.score, reverse=True)
    items = items[:limit]

    return RecommendationListOut(buyer_id=user_id, total=len(items), results=items)


@router.get("/produce/{produce_id}/score", response_model=ProduceScoreOut)
def get_produce_score(produce_id: int, db: Session = Depends(get_db)):
    """Returns the average quality star rating for a produce listing."""
    total = db.query(QualityScore).filter(QualityScore.produce_id == produce_id).count()
    avg = _avg_stars(produce_id, db)
    return ProduceScoreOut(produce_id=produce_id, avg_stars=avg, total_reviews=total)
