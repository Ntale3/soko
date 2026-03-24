import aio_pika
import asyncio
import json
import logging
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal
from app.models.recommendation import OrderEvent, QualityScore, ProduceSummary
from app.cache import invalidate_recommendations, invalidate_score

logger = logging.getLogger(__name__)

# Events this service subscribes to
QUEUES = ["order.placed", "quality.scored", "produce.listed"]


def _handle_order_placed(data: dict, db: Session):
    # Deduplicate by order_id
    exists = db.query(OrderEvent).filter(OrderEvent.order_id == data["order_id"]).first()
    if exists:
        return
    event = OrderEvent(
        order_id=data["order_id"],
        buyer_id=data["buyer_id"],
        produce_id=data["produce_id"],
        farmer_id=data["farmer_id"],
        quantity_kg=data["quantity_kg"],
        total_price=data["total_price"],
    )
    db.add(event)
    db.commit()
    logger.info(f"Stored order event: order_id={data['order_id']}")
    # Buyer's order history changed — their cached recommendations are now stale
    invalidate_recommendations(data["buyer_id"])


def _handle_quality_scored(data: dict, db: Session):
    try:
        score = QualityScore(
            produce_id=data["produce_id"],
            farmer_id=data["farmer_id"],
            buyer_id=data["buyer_id"],
            stars=data["stars"],
        )
        db.add(score)
        db.commit()
        logger.info(f"Stored quality score: produce_id={data['produce_id']} stars={data['stars']}")
    finally:
        # Always invalidate caches when this event arrives — ratings have changed
        # regardless of whether the DB write succeeded.
        invalidate_score(data["produce_id"])
        invalidate_recommendations(data["buyer_id"])


def _handle_produce_listed(data: dict, db: Session):
    # Upsert — update if already exists
    existing = db.query(ProduceSummary).filter(
        ProduceSummary.produce_id == data["produce_id"]
    ).first()
    if existing:
        existing.name = data["name"]
        existing.category = data["category"]
        existing.district = data["district"]
        existing.price_per_unit = data["price_per_unit"]
        existing.unit = data["unit"]
    else:
        summary = ProduceSummary(
            produce_id=data["produce_id"],
            farmer_id=data["farmer_id"],
            name=data["name"],
            category=data["category"],
            district=data["district"],
            price_per_unit=data["price_per_unit"],
            unit=data["unit"],
        )
        db.add(summary)
    db.commit()
    logger.info(f"Synced produce summary: produce_id={data['produce_id']}")


HANDLERS = {
    "order.placed": _handle_order_placed,
    "quality.scored": _handle_quality_scored,
    "produce.listed": _handle_produce_listed,
}


async def _consume_queue(channel: aio_pika.Channel, queue_name: str):
    queue = await channel.declare_queue(queue_name, durable=True)

    async def on_message(message: aio_pika.IncomingMessage):
        async with message.process():
            try:
                payload = json.loads(message.body)
                event_type = payload.get("event", queue_name)
                data = payload.get("data", {})
                handler = HANDLERS.get(event_type)
                if handler:
                    db: Session = SessionLocal()
                    try:
                        handler(data, db)
                    finally:
                        db.close()
                else:
                    logger.warning(f"No handler for event: {event_type}")
            except Exception as e:
                logger.error(f"Error processing message from {queue_name}: {e}")

    await queue.consume(on_message)
    logger.info(f"Subscribed to queue: {queue_name}")


async def _subscribe(connection: aio_pika.RobustConnection):
    """Open a fresh channel and register all queue consumers."""
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=10)
    for queue_name in QUEUES:
        await _consume_queue(channel, queue_name)
    logger.info("Recommendation consumer running — waiting for events.")


async def start_consumer():
    """
    Connects to RabbitMQ with retry and starts consuming all queues.
    Re-subscribes automatically after any reconnect.
    Runs as a persistent background task for the service lifetime.
    """
    while True:
        try:
            connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URL,
                reconnect_interval=5,
            )

            # Re-subscribe every time the connection is re-established
            async def on_reconnect(conn: aio_pika.RobustConnection):
                try:
                    await _subscribe(conn)
                    logger.info("Re-subscribed to all queues after reconnect.")
                except Exception as exc:
                    logger.error(f"Re-subscribe failed: {exc}")

            connection.reconnect_callbacks.add(on_reconnect)

            await _subscribe(connection)

            # Keep alive — the robust connection handles reconnects via the callback
            await asyncio.Future()

        except asyncio.CancelledError:
            logger.info("Consumer task cancelled — shutting down.")
            break
        except Exception as e:
            logger.error(f"Consumer connection error: {e}. Retrying in 5s...")
            await asyncio.sleep(5)
