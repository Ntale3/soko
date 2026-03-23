# Soko – Agricultural Marketplace Backend

A microservices backend for a digital agricultural marketplace connecting farmers and buyers in Uganda.
Built with **FastAPI**, **PostgreSQL**, **RabbitMQ**, and **Docker Compose**.

---

## Architecture

```
                        ┌──────────────┐
                        │  Nginx :80   │  ← API Gateway (rate limiting, routing)
                        └──────┬───────┘
              ┌─────────┬──────┼──────┬─────────┐
              ▼         ▼      ▼      ▼         ▼
         Auth:8001  Farmer:8002  Buyer:8003  Produce:8004  Recommendation:8005
              │         │         │         │              │
              ▼         ▼         ▼         ▼              ▼
          auth_db  farmer_db  buyer_db  produce_db      recoo_db
                              │         │
                              └────┬────┘
                                   ▼
                              RabbitMQ :5672
```

Each service owns its own Postgres database. Services communicate via HTTP (synchronous) and RabbitMQ (async events).

---

## Services

| Service | Port | Docs | Responsibility |
|---|---|---|---|
| Auth | 8001 | `/docs` | Registration, login, JWT issuance |
| Farmer | 8002 | `/docs` | Farmer profiles, farms |
| Buyer | 8003 | `/docs` | Buyer profiles, orders, reviews |
| Produce | 8004 | `/docs` | Produce listings, stock management |
| Recommendation | 8005 | `/docs` | Personalised feed, quality scores |
| RabbitMQ UI | 15672 | — | `guest` / `guest` |

---

## Quick Start

```bash
# Clone and start everything
git clone <repo-url>
cd soko

docker compose up --build
```

All services start with health checks. The first boot creates all database tables automatically.

**Access the APIs:**
- Gateway: `http://localhost:80`
- Individual services: `http://localhost:800{1-5}/docs`

---

## Core User Flows

### Farmer flow
```
POST /auth/register          { email, password, role: "farmer" }
POST /auth/login             → JWT token
POST /farmers/profile        Create profile
POST /produce/               List produce
GET  /farmer/orders/         See incoming orders
PATCH /farmer/orders/{id}/status  { new_status: "confirmed" | "completed" | "rejected" }
```

### Buyer flow
```
POST /auth/register          { email, password, role: "buyer" }
POST /auth/login             → JWT token
POST /buyers/profile         Create profile
GET  /produce/               Browse listings (search, filter by category/district/price)
POST /orders/                Place order
PATCH /orders/{id}/cancel    Cancel pending order
POST /reviews/{order_id}     Leave review (order must be "completed")
GET  /recommendations/       Personalised produce feed
```

### Token refresh
```
POST /auth/refresh           Send valid JWT → get new JWT with fresh expiry
```

---

## API Reference

### Auth Service `:8001`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | — | Register (role: `farmer` or `buyer`) |
| POST | `/auth/login` | — | Login (form data) → JWT |
| GET | `/auth/me` | JWT | Current user info |
| POST | `/auth/refresh` | JWT | Refresh token |

### Farmer Service `:8002`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/farmers/profile` | farmer | Create profile |
| GET | `/farmers/profile` | farmer | Own profile |
| PATCH | `/farmers/profile` | farmer | Update profile |
| GET | `/farmers/` | public | Browse all farmers |
| GET | `/farmers/{id}` | public | Farmer by profile ID |
| GET | `/farmers/by-user/{user_id}` | public | Farmer by auth user ID |
| POST | `/farmers/farms` | farmer | Add farm |
| GET | `/farmers/farms/mine` | farmer | Own farms |

### Buyer Service `:8003`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/buyers/profile` | buyer | Create profile |
| GET | `/buyers/profile` | buyer | Own profile |
| POST | `/orders/` | buyer | Place order |
| GET | `/orders/` | buyer | List own orders |
| GET | `/orders/{id}` | buyer | Order detail |
| PATCH | `/orders/{id}/cancel` | buyer | Cancel pending order |
| POST | `/reviews/{order_id}` | buyer | Review completed order |
| GET | `/farmer/orders/` | farmer | List orders for farmer's produce |
| GET | `/farmer/orders/{id}` | farmer | Order detail |
| PATCH | `/farmer/orders/{id}/status` | farmer | Advance order status |

### Produce Service `:8004`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/produce/` | farmer | Create listing |
| GET | `/produce/` | public | Search/browse listings |
| GET | `/produce/{id}` | public | Single listing |
| PATCH | `/produce/{id}` | farmer | Update own listing |
| DELETE | `/produce/{id}` | farmer | Delete own listing |
| GET | `/produce/farmer/mine` | farmer | Own listings |
| GET | `/produce/prices/predictions` | public | Avg price per category |
| PATCH | `/produce/{id}/reduce-stock` | internal | Reduce stock (called by Buyer service) |

### Recommendation Service `:8005`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/recommendations/` | JWT | Personalised feed |
| GET | `/recommendations/produce/{id}/score` | public | Avg score for a listing |

---

## Order Status Transitions

```
placed → pending
          ├─→ confirmed  (farmer confirms)
          │     └─→ completed  (farmer marks done → buyer can review)
          ├─→ rejected   (farmer rejects)
          └─→ cancelled  (buyer cancels)
```

---

## RabbitMQ Events

| Event | Publisher | Consumers |
|---|---|---|
| `farmer.registered` | Farmer | — |
| `farm.created` | Farmer | — |
| `produce.listed` | Produce | Recommendation |
| `order.placed` | Buyer | Recommendation |
| `order.completed` | Buyer | — |
| `quality.scored` | Buyer | Produce (updates avg_rating), Recommendation |

All queues are durable. Payloads follow the schema in [CONTRACTS.md](CONTRACTS.md).

---

## Produce Categories

`vegetables` · `grains` · `fruits` · `cash_crops` · `dairy` · `herbs` · `livestock` · `other`

---

## Environment Variables

Each service reads config from environment variables (set in `docker-compose.yml`):

| Variable | Services | Description |
|---|---|---|
| `DATABASE_URL` | all | PostgreSQL connection string |
| `RABBITMQ_URL` | all except auth | `amqp://guest:guest@rabbitmq:5672/` |
| `SECRET_KEY` | auth, produce, buyer, farmer, recommendation | JWT signing key |
| `ALGORITHM` | auth, produce, buyer, farmer, recommendation | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | auth | Token lifetime (default 30) |
| `PRODUCE_SERVICE_URL` | buyer | `http://produce_service:8004` |
| `FARMER_SERVICE_URL` | produce | `http://farmer_service:8002` |

---

## Running Tests

Integration tests hit the real services over HTTP (no mocks). Start all services first.

```bash
pip install pytest httpx
pytest tests/integration/ -v
```

Tests cover: health checks, auth, farmer profiles, produce listings, order placement, stock reduction, reviews, recommendation event propagation.

---

## Project Structure

```
soko/
├── docker-compose.yml
├── nginx/
│   └── nginx.conf
├── services/
│   ├── auth/
│   ├── farmer/
│   ├── buyer/
│   ├── produce/
│   └── recommendation/
└── tests/
    └── integration/
        ├── conftest.py      ← session-scoped fixtures
        ├── helpers.py       ← shared BASE_URLS, auth helpers
        └── test_full_flow.py
```

Each service follows the same internal layout:
```
service/
├── Dockerfile
├── requirements.txt
└── app/
    ├── main.py         ← FastAPI app + lifespan
    ├── config.py       ← pydantic-settings
    ├── database.py     ← SQLAlchemy engine + get_db
    ├── dependencies.py ← JWT auth dependencies
    ├── messaging.py    ← RabbitMQ publisher (+ consumer where needed)
    ├── schemas.py      ← Pydantic request/response models
    ├── models/         ← SQLAlchemy ORM models
    └── routers/        ← FastAPI route handlers
```

---

## Known Limitations (pre-production)

- **No Alembic** — schema changes require dropping and recreating the affected DB volume
- **Shared JWT secret** — all services use the same key; use a secrets manager in production
- **`/produce/{id}/reduce-stock` is unauthenticated** — secure with an internal API key in production
- **No password reset** — requires an email provider integration
- **No payment integration** — `PaymentStatus` model exists; Mobile Money (MTN/Airtel) not yet wired up
