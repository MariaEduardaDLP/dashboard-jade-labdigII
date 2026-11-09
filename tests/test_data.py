from datetime import datetime
import json

import pytest
import requests

from shared.catalog import MESSAGES
from frontend.jade.data import (
    DataSourceError,
    demo_events,
    fetch_api_events,
    fetch_supabase_events,
    parse_events,
)

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
    monkeypatch.setattr("frontend.jade.data.requests.get", timeout)
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
    monkeypatch.setattr("frontend.jade.data.requests.get", respond)
    assert fetch_api_events("http://localhost:8000/api/")["id"].tolist() == ["a"]


def test_supabase_uses_publishable_key_and_fetches_all_pages(monkeypatch):
    calls = []

    def respond(url, params, headers, timeout):
        calls.append((url, params.copy(), headers.copy(), timeout))
        response = requests.Response()
        response.status_code = 200
        if params["offset"] == 0:
            response._content = json.dumps([
                {
                    "id": f"event-{index}",
                    "message_id": "agua",
                    "requested_at": "2026-10-27T12:00:00Z",
                    "attended_at": None,
                }
                for index in range(1000)
            ]).encode()
        else:
            response._content = b"[]"
        return response

    monkeypatch.setattr("frontend.jade.data.requests.get", respond)
    result = fetch_supabase_events(
        "https://jade-project.supabase.co/",
        "sb_publishable_example",
    )

    assert len(result) == 1000
    assert result["id"].iloc[0] == "event-0"
    assert [call[1]["offset"] for call in calls] == [0, 1000]
    assert all(call[1]["limit"] == 1000 for call in calls)
    assert all(call[2]["apikey"] == "sb_publishable_example" for call in calls)
    assert all(call[3] == 15 for call in calls)


@pytest.mark.parametrize(
    ("project_url", "publishable_key"),
    [
        ("http://jade-project.supabase.co", "sb_publishable_example"),
        ("https://jade-project.supabase.co", ""),
        ("https://jade-project.supabase.co", "sb_secret_do_not_use"),
    ],
)
def test_supabase_rejects_invalid_public_configuration(project_url, publishable_key):
    with pytest.raises(DataSourceError):
        fetch_supabase_events(project_url, publishable_key)
