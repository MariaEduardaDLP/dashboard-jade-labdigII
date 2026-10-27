from datetime import datetime

import pytest
import requests

from jade.catalog import MESSAGES
from jade.data import DataSourceError, demo_events, fetch_api_events, parse_events

VALID = {"id": "a", "message_id": "agua", "requested_at": "2026-10-27T12:00:00Z", "attended_at": None}


@pytest.mark.parametrize("payload", [
    {}, [None], [{**VALID, "id": ""}], [VALID, VALID],
    [{**VALID, "message_id": "inexistente"}],
    [{**VALID, "message_id": []}],
    [{**VALID, "requested_at": "2026-10-27T12:00:00"}],
    [{**VALID, "requested_at": "ontem"}],
    [{key: value for key, value in VALID.items() if key != "attended_at"}],
    [{**VALID, "attended_at": "2026-10-27T11:59:59Z"}],
])
def test_invalid_api_records_are_rejected(payload):
    with pytest.raises(DataSourceError):
        parse_events(payload)


def test_demo_has_ten_messages_and_no_future_events():
    now = datetime.fromisoformat("2026-10-27T10:00:00-03:00")
    frame = demo_events(now)
    assert set(frame["message_id"]) == {message.id for message in MESSAGES}
    assert frame["requested_at"].max() <= now
    assert frame["attended_at"].dropna().max() <= now
    assert frame["response_minutes"].dropna().ge(0).all()
    assert frame["id"].is_unique
    assert frame.equals(demo_events(now))


def test_api_timeout_reports_failure_without_simulated_fallback(monkeypatch):
    def timeout(*args, **kwargs):
        raise requests.Timeout()
    monkeypatch.setattr("jade.data.requests.get", timeout)
    with pytest.raises(DataSourceError, match="Não foi possível carregar"):
        fetch_api_events("http://localhost:8000")


def test_api_uses_configured_prefix_and_validates_response(monkeypatch):
    def respond(url, timeout):
        assert url == "http://localhost:8000/api/events"
        assert timeout == 10
        response = requests.Response()
        response.status_code = 200
        response._content = b'[{"id":"a","message_id":"agua","requested_at":"2026-10-27T12:00:00Z","attended_at":null}]'
        return response
    monkeypatch.setattr("jade.data.requests.get", respond)
    assert fetch_api_events("http://localhost:8000/api/")["id"].tolist() == ["a"]
