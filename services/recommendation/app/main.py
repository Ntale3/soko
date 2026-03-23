import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import Base, engine
import app.models  # ensure all models are registered with Base
from app.routers.recommendations import router as rec_router
from app.messaging import start_consumer

# Ensure app-level INFO logs are visible in Docker
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _on_consumer_done(task: asyncio.Task):
    """Surface any unhandled exception from the consumer background task."""
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.error(f"Consumer task crashed: {exc}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    consumer_task = asyncio.create_task(start_consumer())
    consumer_task.add_done_callback(_on_consumer_done)
    logger.info("RabbitMQ consumer task started.")

    yield

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    logger.info("RabbitMQ consumer task stopped.")


app = FastAPI(
    title="Soko – Recommendation Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(rec_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "recommendation"}
