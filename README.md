# AgriMarket – Microservices (FastAPI + Docker)

## Project Structure
```
agrimarket/
├── docker-compose.yml        ← all services + DBs + RabbitMQ + Nginx
├── nginx/
│   └── nginx.conf            ← routes /auth/ /farmer/ /buyer/ etc.
└── services/
    ├── auth/                 ← COMPLETE TEMPLATE ✅
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   └── app/
    │       ├── main.py       ← FastAPI app + lifespan (creates tables)
    │       ├── config.py     ← pydantic-settings reads env vars
    │       ├── database.py   ← SQLAlchemy engine + get_db()
    │       ├── schemas.py    ← Pydantic request/response models
    │       ├── security.py   ← JWT + bcrypt (auth only)
    │       ├── models/
    │       │   └── user.py   ← SQLAlchemy ORM model
    │       └── routers/
    │           └── auth.py   ← POST /register, POST /login, GET /me
    ├── farmer/               ← copy auth/, change port + models
    ├── buyer/                ← copy auth/, change port + models
    ├── produce/              ← copy auth/, change port + models
    └── recommendation/       ← copy auth/, change port + models
```

---

## Replication Guide for Other Services

### 1. Copy the auth/ folder
```bash
cp -r services/auth services/farmer
```

### 2. Change the port in Dockerfile
```dockerfile
# farmer/Dockerfile  — change 8001 → 8002
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
```

### 3. Update main.py title
```python
app = FastAPI(title="AgriMarket – Farmer Service", ...)
```

### 4. Replace models/user.py with your domain model
Example for farmer:
```python
class Farm(Base):
    __tablename__ = "farms"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, nullable=False)   # FK to auth_db user
    farm_name  = Column(String, nullable=False)
    location   = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 5. Update schemas.py + routers/ for your new model

### 6. Add RabbitMQ publishing (for Farmer, Buyer, Produce)
```python
# In your router, after a successful DB write:
import aio_pika, json, os

async def publish_event(event_type: str, data: dict):
    conn = await aio_pika.connect_robust(os.getenv("RABBITMQ_URL"))
    async with conn:
        channel = await conn.channel()
        await channel.default_exchange.publish(
            aio_pika.Message(body=json.dumps({"event": event_type, "data": data}).encode()),
            routing_key=event_type,   # e.g. "produce.listed"
        )
```
Add `aio_pika==9.4.1` to requirements.txt for those services.

---

## Running the project

```bash
# First time — build everything
docker-compose up --build

# After first run
docker-compose up

# Tear down (keep DB data)
docker-compose down

# Tear down + wipe all DB volumes
docker-compose down -v
```

## Endpoints after startup
| Service        | Direct         | Via Gateway           |
|----------------|----------------|-----------------------|
| Auth           | :8001/docs     | /auth/docs            |
| Farmer         | :8002/docs     | /farmer/docs          |
| Buyer          | :8003/docs     | /buyer/docs           |
| Produce        | :8004/docs     | /produce/docs         |
| Recommendation | :8005/docs     | /recommendations/docs |
| RabbitMQ UI    | :15672         | guest / guest         |

## Port reference (from your architecture diagram)
- 8001 Auth
- 8002 Farmer
- 8003 Buyer
- 8004 Produce
- 8005 Recommendation
- 8006 Notification Service (Phase 6)
- 8007 ML Pipeline Service (Phase 6)
