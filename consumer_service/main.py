import asyncio
import logging
import os
import signal

from consumer_service.consumer import ClickEventConsumer
from consumer_service.cassandra_client import init_cassandra

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

    session = init_cassandra()

    consumer = ClickEventConsumer(bootstrap_servers=bootstrap_servers)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    await consumer.start()
    try:
        consume_task = asyncio.create_task(consumer.consume())
        await stop_event.wait()
        consume_task.cancel()
    finally:
        await consumer.stop()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())