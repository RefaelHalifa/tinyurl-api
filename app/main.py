from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.database import connect_db, close_db
from app.routes.health import router as health_router
from app.routes import urls
from app.services.kafka_producer import start_producer, stop_producer
from app.services.cassandra_service import cassandra_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # === STARTUP — runs before the app accepts requests ===
    await connect_db()
    print("✅ Connected to MongoDB")
    await start_producer()
    print("✅ Kafka producer started")
    cassandra_service.connect()
    print("✅ Connected to Cassandra")
    yield
    # === SHUTDOWN — runs after the app stops accepting requests ===
    await close_db()
    print("🛑 MongoDB connection closed")
    await stop_producer()
    print("🛑 Kafka producer stopped")
    cassandra_service.disconnect()
    print("🛑 Cassandra connection closed")

app = FastAPI(
    title="TinyURL API",
    description="High-scale URL shortening service with MongoDB, Redis, Kafka, and Cassandra",
    version="1.0.0",
    lifespan=lifespan,
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    messages = [f"{' -> '.join(str(l) for l in e['loc'])}: {e['msg']}" for e in errors]
    return JSONResponse(
        status_code=422,
        content={"detail": messages},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )

app.include_router(health_router, tags=["Health"])
app.include_router(urls.router, tags=["URLs"])