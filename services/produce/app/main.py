import asyncio
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import Base, engine
import app.models
from app.routers.produce import router as produce_router
from app.messaging import init_publisher, close_publisher, start_consumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _on_consumer_done(task: asyncio.Task):
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.error(f"Consumer task crashed: {exc}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    await init_publisher()

    consumer_task = asyncio.create_task(start_consumer())
    consumer_task.add_done_callback(_on_consumer_done)

    yield

    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    await close_publisher()


app = FastAPI(
    title="Soko – Produce Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(produce_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "produce"}
