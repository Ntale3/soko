from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.database import Base, engine
from app.routers import conversations, messages, ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Soko Messaging Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(ws.router,            prefix="/messaging")
app.include_router(conversations.router, prefix="/messaging/conversations")
app.include_router(messages.router,      prefix="/messaging/conversations")


@app.get("/health")
def health():
    return {"status": "ok", "service": "messaging"}