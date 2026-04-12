from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.database import Base, engine
from app.routers import listings, images, reviews, internal


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Soko Produce Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(internal.router, prefix="/internal")
app.include_router(images.router,   prefix="/listings")
app.include_router(reviews.router,  prefix="/listings")
app.include_router(listings.router, prefix="/listings")


@app.get("/health")
def health():
    return {"status": "ok", "service": "produce"}