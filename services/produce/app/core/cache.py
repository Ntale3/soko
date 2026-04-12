import json
import logging
import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── TTLs (seconds)
TTL_LISTINGS      = 300    # 5 min  — browse page
TTL_LISTING       = 600    # 10 min — single product detail
TTL_FARMER_LISTINGS = 300  # 5 min  — farmer's public listings
TTL_PRICE_SUGGEST = 600    # 10 min — price suggestion aggregates
TTL_REVIEWS       = 300    # 5 min  — product reviews

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _client



# Key builders — one per cache domain

def _listings_key(
    category:  str | None,
    district:  str | None,
    fresh:     bool | None,
    min_price: float | None,
    max_price: float | None,
    search:    str | None,
    page:      int,
    limit:     int,
) -> str:
    return (
        f"listings:"
        f"{category or 'all'}:"
        f"{district or 'all'}:"
        f"{str(fresh) if fresh is not None else 'all'}:"
        f"{min_price or '0'}:"
        f"{max_price or 'inf'}:"
        f"{search or ''}:"
        f"p{page}:l{limit}"
    )


def _listing_key(slug: str) -> str:
    return f"listing:slug:{slug}"


def _farmer_listings_key(farmer_id: str, page: int, limit: int) -> str:
    return f"farmer_listings:{farmer_id}:p{page}:l{limit}"


def _price_suggestion_key(category: str, unit: str, district: str | None) -> str:
    return f"price_suggestion:{category}:{unit}:{district or 'all'}"


def _reviews_key(listing_id: str, page: int, limit: int) -> str:
    return f"reviews:{listing_id}:p{page}:l{limit}"



# Generic helpers
def _get(key: str) -> dict | list | None:
    try:
        raw = get_redis().get(key)
        return json.loads(raw) if raw else None
    except Exception as e:
        logger.warning(f"Redis read error [{key}]: {e}")
        return None


def _set(key: str, data: dict | list, ttl: int) -> None:
    try:
        get_redis().setex(key, ttl, json.dumps(data))
    except Exception as e:
        logger.warning(f"Redis write error [{key}]: {e}")


def _delete_pattern(pattern: str) -> None:
    try:
        keys = get_redis().keys(pattern)
        if keys:
            get_redis().delete(*keys)
            logger.info(f"Cache invalidated: {len(keys)} key(s) matching '{pattern}'")
    except Exception as e:
        logger.warning(f"Redis delete error [{pattern}]: {e}")



# Public listings (browse page)
def get_cached_listings(
    category:  str | None,
    district:  str | None,
    fresh:     bool | None,
    min_price: float | None,
    max_price: float | None,
    search:    str | None,
    page:      int,
    limit:     int,
) -> list | None:
    key = _listings_key(category, district, fresh, min_price, max_price, search, page, limit)
    return _get(key)


def set_cached_listings(
    category:  str | None,
    district:  str | None,
    fresh:     bool | None,
    min_price: float | None,
    max_price: float | None,
    search:    str | None,
    page:      int,
    limit:     int,
    data:      list,
) -> None:
    key = _listings_key(category, district, fresh, min_price, max_price, search, page, limit)
    _set(key, data, TTL_LISTINGS)


def invalidate_listings() -> None:
    """Call when any listing is created, updated, published or archived."""
    _delete_pattern("listings:*")


# Single listing by slug
def get_cached_listing(slug: str) -> dict | None:
    return _get(_listing_key(slug))


def set_cached_listing(slug: str, data: dict) -> None:
    _set(_listing_key(slug), data, TTL_LISTING)


def invalidate_listing(slug: str) -> None:
    """Call when this specific listing is updated."""
    try:
        get_redis().delete(_listing_key(slug))
    except Exception as e:
        logger.warning(f"Redis delete error [listing:{slug}]: {e}")


# Farmer public listings
def get_cached_farmer_listings(farmer_id: str, page: int, limit: int) -> list | None:
    return _get(_farmer_listings_key(farmer_id, page, limit))


def set_cached_farmer_listings(farmer_id: str, page: int, limit: int, data: list) -> None:
    _set(_farmer_listings_key(farmer_id, page, limit), data, TTL_FARMER_LISTINGS)


def invalidate_farmer_listings(farmer_id: str) -> None:
    """Call when farmer creates, updates or archives a listing."""
    _delete_pattern(f"farmer_listings:{farmer_id}:*")


# Price suggestion
def get_cached_price_suggestion(
    category: str,
    unit:     str,
    district: str | None
) -> dict | None:
    return _get(_price_suggestion_key(category, unit, district))


def set_cached_price_suggestion(
    category: str,
    unit:     str,
    district: str | None,
    data:     dict
) -> None:
    _set(_price_suggestion_key(category, unit, district), data, TTL_PRICE_SUGGEST)


def invalidate_price_suggestions() -> None:
    """Call when a new listing is published or a price is updated."""
    _delete_pattern("price_suggestion:*")


# Product reviews
def get_cached_reviews(listing_id: str, page: int, limit: int) -> list | None:
    return _get(_reviews_key(listing_id, page, limit))


def set_cached_reviews(listing_id: str, page: int, limit: int, data: list) -> None:
    _set(_reviews_key(listing_id, page, limit), data, TTL_REVIEWS)


def invalidate_reviews(listing_id: str) -> None:
    """Call when a review is added to this listing."""
    _delete_pattern(f"reviews:{listing_id}:*")