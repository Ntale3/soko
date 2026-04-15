from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.database import Base, engine
from app.routers import orders, internal


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Soko Order Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(internal.router, prefix="/internal")
app.include_router(orders.router,   prefix="/orders")


@app.get("/health")
def health():
    return {"status": "ok", "service": "orders"}