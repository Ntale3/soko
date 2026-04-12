import json
import logging
import redis

from services.produce.app.core.config import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None

PREDICTIONS_TTL = 600  # 10 minutes — price predictions aggregate


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


def _predictions_key(category: str | None, district: str | None) -> str:
    return f"predictions:{category or 'all'}:{district or 'all'}"


def get_cached_predictions(category: str | None, district: str | None) -> dict | None:
    try:
        raw = get_redis().get(_predictions_key(category, district))
        return json.loads(raw) if raw else None
    except Exception as e:
        logger.warning(f"Redis read error (predictions): {e}")
        return None


def set_cached_predictions(category: str | None, district: str | None, data: dict) -> None:
    try:
        get_redis().setex(_predictions_key(category, district), PREDICTIONS_TTL, json.dumps(data))
    except Exception as e:
        logger.warning(f"Redis write error (predictions): {e}")


def invalidate_predictions() -> None:
    """Delete all cached prediction keys when a new listing is created or updated."""
    try:
        keys = get_redis().keys("predictions:*")
        if keys:
            get_redis().delete(*keys)
            logger.info(f"Cache invalidated: {len(keys)} prediction key(s)")
    except Exception as e:
        logger.warning(f"Redis delete error (predictions): {e}")
