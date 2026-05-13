import json
import logging
from aiokafka import AIOKafkaConsumer

logger = logging.getLogger(__name__)

CLICK_EVENTS_TOPIC = "click_events"
GROUP_ID = "tinyurl-consumers"


class ClickEventConsumer:
    def __init__(self, bootstrap_servers: str):
        self._bootstrap_servers = bootstrap_servers
        self._consumer: AIOKafkaConsumer | None = None

    async def start(self):
        self._consumer = AIOKafkaConsumer(
            CLICK_EVENTS_TOPIC,
            bootstrap_servers=self._bootstrap_servers,
            group_id=GROUP_ID,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="earliest",
        )
        await self._consumer.start()
        logger.info("Kafka consumer started — listening on topic: %s", CLICK_EVENTS_TOPIC)

    async def stop(self):
        if self._consumer:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped")

    async def consume(self):
        async for message in self._consumer:
            event = message.value
            logger.info(
                "Received click event: short_code=%s clicked_at=%s",
                event.get("short_code"),
                event.get("clicked_at"),
            )