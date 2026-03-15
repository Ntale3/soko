import aio_pika
import json
import logging
from app.config import settings

logger = logging.getLogger(__name__)


async def publish_event(event_type: str, data: dict):
    """
    Publishes an event to RabbitMQ.
    event_type examples: "farmer.registered", "farm.created"
    """
    try:
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()

            # Declare the queue so it exists before publishing
            queue = await channel.declare_queue(event_type, durable=True)

            message_body = json.dumps({
                "event": event_type,
                "data": data
            }).encode()

            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=message_body,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=event_type,
            )
            logger.info(f"Published event: {event_type}")

    except Exception as e:
        # Don't let messaging failure break the main request
        logger.error(f"Failed to publish event {event_type}: {e}")
