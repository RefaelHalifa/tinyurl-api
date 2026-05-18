import uuid
from datetime import datetime, timezone
from cassandra.cluster import Cluster
from cassandra.policies import RoundRobinPolicy
from app.config import settings

# TIMEUUID stores time as 100-nanosecond intervals since Oct 15, 1582
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_UUID_EPOCH_OFFSET = 122192928000000000  # intervals between 1582 and 1970


def _timeuuid_to_datetime(timeuuid) -> datetime:
    intervals = timeuuid.time - _UUID_EPOCH_OFFSET
    return datetime.fromtimestamp(intervals / 1e7, tz=timezone.utc)


class CassandraService:
    def __init__(self):
        self._cluster = None
        self._session = None
        self._count_stmt = None
        self._select_stmt = None

    def connect(self):
        self._cluster = Cluster(
            contact_points=[settings.cassandra_host],
            load_balancing_policy=RoundRobinPolicy(),
            protocol_version=5,
        )
        self._session = self._cluster.connect("tinyurl")
        self._count_stmt = self._session.prepare(
            "SELECT COUNT(*) FROM click_events WHERE short_code = ?"
        )
        self._select_stmt = self._session.prepare(
            "SELECT clicked_at FROM click_events WHERE short_code = ?"
        )

    def disconnect(self):
        if self._cluster:
            self._cluster.shutdown()

    def get_click_count(self, short_code: str) -> int:
        row = self._session.execute(self._count_stmt, (short_code,)).one()
        return row[0] if row else 0

    def get_clicks(self, short_code: str) -> list[dict]:
        rows = self._session.execute(self._select_stmt, (short_code,))
        return [{"clicked_at": _timeuuid_to_datetime(row.clicked_at)} for row in rows]


cassandra_service = CassandraService()