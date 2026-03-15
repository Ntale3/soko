from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import Base, engine
from app.routers.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="AgriMarket – Auth Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "auth"}
