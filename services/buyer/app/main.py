from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import Base, engine
import app.models  # ensures all models are registered with SQLAlchemy
from app.routers.buyer import router as buyer_router
from app.routers.orders import router as orders_router
from app.routers.reviews import router as reviews_router
from app.routers.produce import router as produce_router
from app.routers.farmer_orders import router as farmer_orders_router
from app.messaging import init_publisher, close_publisher


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    await init_publisher()
    yield
    await close_publisher()


app = FastAPI(
    title="Soko – Buyer Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(buyer_router)
app.include_router(orders_router)
app.include_router(reviews_router)
app.include_router(produce_router)
app.include_router(farmer_orders_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "buyer"}
