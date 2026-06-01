# TinyURL API

A high-scale URL shortening service built with a modern async Python stack and a full event-driven analytics pipeline.

Built as a portfolio backend project to demonstrate production-relevant architecture: caching, event streaming, and time-series analytics.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI (async) |
| Primary DB | MongoDB + Motor |
| Cache | Redis (aioredis, sliding TTL) |
| Event streaming | Apache Kafka |
| Analytics DB | Apache Cassandra |
| Infrastructure | Docker Compose (6 services) |

---

## Architecture

```
Client
  │
  ▼
FastAPI App
  ├── POST /shorten         → MongoDB (write)
  ├── GET /{code}           → Redis (cache hit) → MongoDB (miss) → Kafka (click event)
  ├── GET /stats/{code}     → MongoDB + Cassandra (click count)
  ├── GET /analytics/{code} → Cassandra (full click history)
  └── GET /health           → uptime + DB status

Kafka Consumer (standalone service)
  └── click_events topic → Cassandra (click rows)
```

Every redirect publishes a click event to Kafka. A standalone consumer service reads those events and writes them to Cassandra, keeping the read path fast and the analytics pipeline decoupled from the API.

---

## Features

- Shorten any URL with an auto-generated Base62 code (6 chars, 56 billion combinations)
- Optional custom alias with collision detection
- Configurable TTL per URL (default: 30 days); expired URLs return `410 Gone`
- Redis cache with sliding TTL — hot URLs stay cached, cold ones expire naturally
- Click events streamed to Kafka asynchronously on every redirect
- Full click history queryable per short code, stored in Cassandra with `TIMEUUID` ordering
- Global error handling and Pydantic input validation
- Interactive API docs at `/docs` (Swagger UI)

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/shorten` | Create a short URL |
| `GET` | `/{code}` | Redirect to original URL |
| `GET` | `/stats/{code}` | Total clicks + URL metadata |
| `GET` | `/analytics/{code}` | Full click history with timestamps |
| `GET` | `/health` | Service health + uptime |

### POST /shorten

Request body:

```json
{
  "original_url": "https://example.com/some/very/long/path",
  "custom_code": "my-link",
  "ttl_days": 7
}
```

Response:

```json
{
  "short_code": "my-link",
  "short_url": "http://localhost:8000/my-link",
  "original_url": "https://example.com/some/very/long/path",
  "created_at": "2026-06-01T10:00:00Z",
  "expires_at": "2026-06-08T10:00:00Z"
}
```

---

## Running Locally

**Prerequisites**: Docker + Docker Compose

```bash
git clone https://github.com/RefaelHalifa/tinyurl-api.git
cd tinyurl-api
docker-compose up --build
```

The API will be available at `http://localhost:8000`.  
Swagger docs: `http://localhost:8000/docs`

### Environment Variables

```env
MONGO_URL=mongodb://mongo:27017
MONGO_DB_NAME=tinyurl
REDIS_URL=redis://redis:6379
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_TOPIC=click_events
CASSANDRA_HOST=cassandra
CASSANDRA_KEYSPACE=tinyurl_analytics
CACHE_TTL=3600
```

---

## Project Structure

```
tinyurl-api/
├── app/
│   ├── main.py               # FastAPI app, lifespan, error handlers
│   ├── config.py             # Pydantic settings
│   ├── database.py           # MongoDB Motor client
│   ├── models/               # Pydantic request/response models
│   ├── routes/               # API route handlers
│   └── services/
│       ├── shortener.py      # Base62 code generation
│       ├── cache_service.py  # Redis get/set/delete
│       ├── kafka_producer.py
│       └── cassandra_service.py
├── consumer_service/         # Standalone Kafka consumer → Cassandra writer
├── docker-compose.yml        # Full 6-service stack
└── requirements.txt
```

---

## Key Design Decisions

- **Redis sliding TTL**: cache TTL resets on every access, keeping hot URLs cached indefinitely while cold ones expire automatically.
- **Kafka decoupling**: the redirect path never waits for analytics — click events are published async and processed by a separate consumer.
- **Cassandra TIMEUUID**: click rows use `uuid1()` as the clustering key, giving sub-millisecond uniqueness and natural time ordering with no collision risk.
- **Route order**: `GET /stats/{code}` is registered before `GET /{code}` — FastAPI evaluates routes in order and the wildcard would otherwise hijack `/stats`.
- **Standalone consumer**: the Kafka consumer runs as a separate Docker service, making it independently scalable and restartable without touching the API.

---

## Author

**Refael Halifa** · [github.com/RefaelHalifa](https://github.com/RefaelHalifa) · rafaelhalifa@gmail.com
