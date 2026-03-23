import asyncio
import aio_pika
import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)

_connection: aio_pika.RobustConnection | None = None
_channel: aio_pika.Channel | None = None


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
