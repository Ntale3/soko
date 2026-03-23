from pydantic import BaseModel
from datetime import datetime


class RecommendationItem(BaseModel):
    produce_id: int
    farmer_id: int
    name: str
    category: str
    district: str
    price_per_unit: float
    unit: str
    avg_stars: float | None
    score: float  # 0.0–1.0 relevance score
    reason: str


class RecommendationListOut(BaseModel):
    buyer_id: int
    total: int
    results: list[RecommendationItem]


class ProduceScoreOut(BaseModel):
    produce_id: int
    avg_stars: float | None
    total_reviews: int
