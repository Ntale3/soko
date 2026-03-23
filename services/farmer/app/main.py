from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import Base, engine
from app.routers.farmer import router as farmer_router
from app.messaging import init_publisher, close_publisher


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    await init_publisher()
    yield
    await close_publisher()


app = FastAPI(
    title="Soko – Farmer Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(farmer_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "farmer"}
