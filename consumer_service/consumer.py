import json
import logging
import uuid
from aiokafka import AIOKafkaConsumer
from cassandra.cluster import Session

logger = logging.getLogger(__name__)

CLICK_EVENTS_TOPIC = "click_events"
GROUP_ID = "tinyurl-consumers"

INSERT_CLICK_CQL = """
INSERT INTO tinyurl.click_events (short_code, clicked_at, country, user_agent)
VALUES (?, ?, ?, ?)
"""


class ClickEventConsumer:
    def __init__(self, bootstrap_servers: str, cassandra_session: Session):
        self._bootstrap_servers = bootstrap_servers
        self._cassandra_session = cassandra_session
        self._insert_stmt = cassandra_session.prepare(INSERT_CLICK_CQL)
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
            short_code = event.get("short_code")
            logger.info(
                "Received click event: short_code=%s clicked_at=%s",
                short_code,
                event.get("clicked_at"),
            )
            self._cassandra_session.execute(
                self._insert_stmt,
                (short_code, uuid.uuid1(), None, None),
            )
            logger.info("Persisted click event to Cassandra: short_code=%s", short_code)