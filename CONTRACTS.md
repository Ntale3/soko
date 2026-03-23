# Soko – Service Contracts

Defines the interfaces between services — HTTP and RabbitMQ.
Update this file when adding or changing any cross-service interface.

---

## RabbitMQ Event Payloads

All messages follow the envelope `{ "event": "<name>", "data": { ... } }`.
All queues are declared **durable**.

---

### `farmer.registered`
Published by: **Farmer service** after profile creation.

```json
{
  "event": "farmer.registered",
  "data": {
    "farmer_id": 1,
    "user_id": 1,
    "district": "Kampala"
  }
}
```

---

### `farm.created`
Published by: **Farmer service** after a farm is added.

```json
{
  "event": "farm.created",
  "data": {
    "farm_id": 1,
    "farmer_id": 1,
    "location": "Mukono, Central Uganda"
  }
}
```

---

### `produce.listed`
Published by: **Produce service** after a listing is created.
Consumed by: **Recommendation service** (stores `ProduceSummary`).

```json
{
  "event": "produce.listed",
  "data": {
    "produce_id": 3,
    "farmer_id": 1,
    "name": "Maize",
    "category": "grains",
    "district": "Kampala",
    "price_per_unit": 1200.0,
    "unit": "kg"
  }
}
```

---

### `order.placed`
Published by: **Buyer service** after an order is committed to the DB.
Consumed by: **Recommendation service** (stores `OrderEvent`, used to exclude already-ordered produce).

> **Important:** `buyer_id` is the **auth user ID** (JWT `sub`), not the buyer profile ID.
> `farmer_id` is the **auth user ID** of the farmer, not the farmer profile ID.

```json
{
  "event": "order.placed",
  "data": {
    "order_id": 1,
    "produce_id": 3,
    "farmer_id": 1,
    "buyer_id": 2,
    "quantity_kg": 5.0,
    "total_price": 6000.0
  }
}
```

---

### `order.completed`
Published by: **Buyer service** when a farmer marks an order as `completed`.
Consumed by: — (reserved for notification service).

```json
{
  "event": "order.completed",
  "data": {
    "order_id": 1,
    "produce_id": 3,
    "farmer_id": 1,
    "quantity_kg": 5.0,
    "total_price": 6000.0
  }
}
```

---

### `quality.scored`
Published by: **Buyer service** when a buyer submits a review.
Consumed by:
- **Produce service** — updates `avg_rating` and `review_count` on the listing
- **Recommendation service** — stores `QualityScore`

> **Note:** `buyer_id` here is the buyer **profile ID** (not auth user ID).

```json
{
  "event": "quality.scored",
  "data": {
    "order_id": 1,
    "produce_id": 3,
    "farmer_id": 1,
    "buyer_id": 1,
    "stars": 4,
    "comment": "Great tomatoes"
  }
}
```

---

## HTTP Service-to-Service Calls

### Buyer → Produce
Used during order placement to verify stock and reserve it.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/produce/{id}` | Check listing exists, price, available quantity |
| PATCH | `/produce/{id}/reduce-stock` | Deduct ordered quantity |

`reduce-stock` payload:
```json
{ "quantity": 5.0 }
```

### Produce → Farmer
Used at listing creation to denormalise the farmer's display name.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/farmers/by-user/{user_id}` | Retrieve farmer name for storage on listing |

---

## Produce Listing Response Shape

Returned by `GET /produce/` and `GET /produce/{id}`. Frontend-relevant fields:

```json
{
  "id": 3,
  "farmer_id": 1,
  "farmer_name": "John Mukasa",
  "name": "Maize",
  "description": "Fresh dry maize",
  "category": "grains",
  "unit": "kg",
  "quantity": 95.0,
  "price_per_unit": 1200.0,
  "district": "Kampala",
  "is_available": true,
  "avg_rating": 4.2,
  "review_count": 5,
  "created_at": "2026-03-23T08:00:00Z",
  "updated_at": null
}
```

---

## Order Status Transitions

| From | To | Actor |
|---|---|---|
| `pending` | `confirmed` | Farmer |
| `pending` | `rejected` | Farmer |
| `pending` | `cancelled` | Buyer |
| `confirmed` | `completed` | Farmer |

Only `completed` orders can receive a review.

---

## Recommendation Scoring

Scores are computed at request time (not stored) from `ProduceSummary` and `QualityScore` tables:

| Signal | Weight |
|---|---|
| Matching category (based on order history) | 0.4 |
| Matching district | 0.3 |
| Average star rating (normalised 0–1) | 0.3 |

Produce the buyer has already ordered is excluded from results.
