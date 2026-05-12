import json
import logging
from datetime import datetime, timezone
from aiokafka import AIOKafkaProducer
from app.config import settings

logger = logging.getLogger(__name__)

CLICK_EVENTS_TOPIC = "click_events"

# Global producer instance — started once at app startup
_producer: AIOKafkaProducer | None = None


async def start_producer():
    """Start the Kafka producer — call this at app startup."""
    global _producer
    _producer = AIOKafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await _producer.start()
    logger.info("Kafka producer started")


async def stop_producer():
    """Stop the Kafka producer — call this at app shutdown."""
    global _producer
    if _producer:
        await _producer.stop()
        logger.info("Kafka producer stopped")


async def publish_click_event(short_code: str):
    """Publish a click event to the click_events topic."""
    if not _producer:
        logger.warning("Kafka producer not initialized — skipping event")
        return

    event = {
        "short_code": short_code,
        "clicked_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        await _producer.send(CLICK_EVENTS_TOPIC, value=event)
    except Exception as e:
        logger.error(f"Failed to publish click event for {short_code}: {e}")