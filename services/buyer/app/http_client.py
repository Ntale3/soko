import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)


async def get_produce_listing(produce_id: int) -> dict | None:
    """
    Fetches a single produce listing from the Produce service.
    Returns the listing dict or None if not found.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.PRODUCE_SERVICE_URL}/produce/{produce_id}"
            )
            if response.status_code == 200:
                return response.json()
            return None
    except httpx.RequestError as e:
        logger.error(f"Failed to reach Produce service: {e}")
        return None


async def search_produce(
    name: str | None = None,
    district: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    """
    Searches produce listings via the Produce service.
    Returns paginated results.
    """
    params = {"page": page, "page_size": page_size}
    if name:
        params["name"] = name
    if district:
        params["district"] = district
    if min_price is not None:
        params["min_price"] = min_price
    if max_price is not None:
        params["max_price"] = max_price

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.PRODUCE_SERVICE_URL}/produce",
                params=params
            )
            if response.status_code == 200:
                return response.json()
            return {"total": 0, "page": page, "page_size": page_size, "results": []}
    except httpx.RequestError as e:
        logger.error(f"Failed to reach Produce service: {e}")
        return {"total": 0, "page": page, "page_size": page_size, "results": []}


async def reduce_produce_stock(produce_id: int, quantity: float) -> bool:
    """
    Called after order is saved — reduces stock on Produce service.
    Returns True if successful, False otherwise.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.patch(
                f"{settings.PRODUCE_SERVICE_URL}/produce/{produce_id}/reduce-stock",
                json={"quantity": quantity}
            )
            return response.status_code == 200
    except httpx.RequestError as e:
        logger.error(f"Failed to reduce stock for produce {produce_id}: {e}")
        return False
