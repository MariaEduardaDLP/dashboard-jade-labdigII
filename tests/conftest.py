import pytest

from jade.data import parse_events


@pytest.fixture
def events():
    return parse_events([
        {"id": "a", "message_id": "agua", "requested_at": "2026-10-01T10:00:00-03:00", "attended_at": "2026-10-01T10:02:00-03:00"},
        {"id": "b", "message_id": "ajuda", "requested_at": "2026-10-01T10:05:00-03:00", "attended_at": None},
        {"id": "c", "message_id": "agua", "requested_at": "2026-10-01T23:59:00-03:00", "attended_at": "2026-10-02T00:01:00-03:00"},
        {"id": "d", "message_id": "dor", "requested_at": "2026-10-02T02:30:00Z", "attended_at": "2026-10-02T02:30:00Z"},
        {"id": "e", "message_id": "agua", "requested_at": "2026-10-02T03:00:00Z", "attended_at": None},
    ])
