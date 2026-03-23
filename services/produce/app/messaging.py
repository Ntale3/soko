import asyncio
import aio_pika
import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)

_connection: aio_pika.RobustConnection | None = None
_channel: aio_pika.Channel | None = None


# ── Consumer — quality.scored ─────────────────────────────────────────

async def _handle_quality_scored(message: aio_pika.IncomingMessage):
    """Update running avg_rating on the produce listing when a review is submitted."""
    async with message.process():
        try:
            payload = json.loads(message.body)
            data = payload.get("data", {})
            produce_id = data.get("produce_id")
            stars = data.get("stars")
            if produce_id is None or stars is None:
                return

            # Import here to avoid circular imports at module load time
            from app.database import SessionLocal
            from app.models.produce import ProduceListing

            db = SessionLocal()
            try:
                listing = db.query(ProduceListing).filter(
                    ProduceListing.id == produce_id
                ).first()
                if listing:
                    # Incremental running average
                    total = listing.avg_rating * listing.review_count + stars
                    listing.review_count += 1
                    listing.avg_rating = round(total / listing.review_count, 2)
                    db.commit()
                    logger.info(f"Updated avg_rating for produce {produce_id}: {listing.avg_rating}")
            finally:
                db.close()
        except Exception as exc:
            logger.error(f"Error handling quality.scored: {exc}", exc_info=True)


async def start_consumer():
    """Consume quality.scored events and keep the connection alive with auto-reconnect."""
    while True:
        try:
            conn = await aio_pika.connect_robust(settings.RABBITMQ_URL, reconnect_interval=5)
            ch = await conn.channel()
            await ch.set_qos(prefetch_count=10)
            queue = await ch.declare_queue("quality.scored", durable=True)
            await queue.consume(_handle_quality_scored)
            logger.info("Produce service consumer started — listening on quality.scored")
            await asyncio.Future()  # keep alive until cancelled
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(f"Consumer connection error: {exc}. Retrying in 5s…")
            await asyncio.sleep(5)


async def init_publisher(retries: int = 10, delay: float = 3.0):
    global _connection, _channel
    for attempt in range(1, retries + 1):
        try:
            _connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            _channel = await _connection.channel()
            logger.info("RabbitMQ publisher connected.")
            return
        except Exception as e:
            logger.warning(f"RabbitMQ connect attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                await asyncio.sleep(delay)
    logger.error("RabbitMQ publisher could not connect — events will be dropped until reconnect.")


async def close_publisher():
    global _connection, _channel
    if _connection and not _connection.is_closed:
        await _connection.close()
    _channel = None
    _connection = None
    logger.info("RabbitMQ publisher connection closed.")


async def publish_event(event_type: str, data: dict):
    if _channel is None:
        logger.error(f"Publisher not initialised — dropping event {event_type}")
        return
    try:
        await _channel.declare_queue(event_type, durable=True)
        await _channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps({"event": event_type, "data": data}).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=event_type,
        )
        logger.info(f"Published event: {event_type}")
    except Exception as e:
        logger.error(f"Failed to publish event {event_type}: {e}")
