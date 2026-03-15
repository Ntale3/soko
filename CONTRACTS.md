# Soko – Service Contracts

This file defines the agreed interfaces between services.
**Both parties must update and agree on this file before changing any interface.**

---

## Recommendation Service Contract

### Responsibility split
| Owner | Scope |
|-------|-------|
| Backend (Ario) | FastAPI endpoints, recoo_db schema, RabbitMQ event publishing |
| ML (Teammate) | ML model logic, writing results to recoo_db, consuming events |

---

### Events Backend Publishes → ML Consumes

**Queue:** `recommendation.requested`
```json
{
  "event": "recommendation.requested",
  "data": {
    "buyer_id": 1,
    "district": "Kampala",
    "produce_type": "tomatoes",
    "requested_at": "2026-03-14T12:00:00Z"
  }
}
```

**Queue:** `transaction.completed`
```json
{
  "event": "transaction.completed",
  "data": {
    "buyer_id": 1,
    "produce_id": 4,
    "farmer_id": 2,
    "quantity_kg": 50,
    "completed_at": "2026-03-14T12:00:00Z"
  }
}
```

---

### Database Table ML Writes To (recoo_db)

Table: `recommendations`
| Column | Type | Notes |
|--------|------|-------|
| id | Integer | Primary key |
| buyer_id | Integer | From auth_db |
| produce_id | Integer | From produce_db |
| farmer_id | Integer | From farmer_db |
| score | Float | 0.0 – 1.0 confidence |
| reason | String | e.g. "Based on past purchases" |
| created_at | DateTime | When generated |

---

### API Endpoints Backend Exposes (reads from recoo_db)

```
GET /recommendations/{buyer_id}
→ Returns top 5 recommendations for a buyer

GET /recommendations/{buyer_id}/history
→ Returns past recommendations
```

---

## RabbitMQ Event Reference

All events published across services:

| Event | Publisher | Consumers |
|-------|-----------|-----------|
| `farmer.registered` | Farmer Service | Recommendation |
| `farm.created` | Farmer Service | — |
| `produce.listed` | Produce Service | Recommendation |
| `transaction.completed` | Buyer Service | Recommendation, Notification |
| `recommendation.requested` | Buyer Service | Recommendation (ML) |
| `quality.scored` | Produce Service | Recommendation |
