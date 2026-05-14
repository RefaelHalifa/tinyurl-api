import logging
import os
from cassandra.cluster import Cluster
from cassandra.policies import RoundRobinPolicy

logger = logging.getLogger(__name__)

KEYSPACE = "tinyurl"

CREATE_KEYSPACE_CQL = """
CREATE KEYSPACE IF NOT EXISTS tinyurl
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}
"""

CREATE_TABLE_CQL = """
CREATE TABLE IF NOT EXISTS tinyurl.click_events (
    short_code  TEXT,
    clicked_at  TIMEUUID,
    country     TEXT,
    user_agent  TEXT,
    PRIMARY KEY (short_code, clicked_at)
) WITH CLUSTERING ORDER BY (clicked_at DESC)
"""


def init_cassandra():
    host = os.getenv("CASSANDRA_HOST", "localhost")

    cluster = Cluster(
        contact_points=[host],
        load_balancing_policy=RoundRobinPolicy(),
        protocol_version=5,
    )
    session = cluster.connect()
    logger.info("Connected to Cassandra at %s", host)

    session.execute(CREATE_KEYSPACE_CQL)
    session.execute(CREATE_TABLE_CQL)
    logger.info("Keyspace and table ready")

    return session