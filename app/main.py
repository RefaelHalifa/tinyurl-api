from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.database import connect_db, close_db
from app.routes.health import router as health_router
from app.routes import urls
from app.services.kafka_producer import start_producer, stop_producer

@asynccontextmanager
async def lifespan(app: FastAPI):
    # === STARTUP — runs before the app accepts requests ===
    await connect_db()
    print("✅ Connected to MongoDB")
    await start_producer()
    print("✅ Kafka producer started")
    yield
    # === SHUTDOWN — runs after the app stops accepting requests ===
    await close_db()
    print("🛑 MongoDB connection closed")
    await stop_producer()
    print("🛑 Kafka producer stopped")

app = FastAPI(
    title="TinyURL API",
    description="High-scale URL shortening service with MongoDB, Redis, Kafka, and Cassandra",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health_router, tags=["Health"])
app.include_router(urls.router, tags=["URLs"])