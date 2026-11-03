import asyncio
from datetime import datetime, timezone
import os
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url

from backend.database import _normalize_database_url, create_database
from backend.events import Event, SerialProcessingError, process_serial_message
from backend.main import create_app
from backend.serial_protocol import SerialMessage
from backend.serial_listener import SerialListener
from frontend.jade.data import parse_events


@pytest.fixture
def postgres_test_database_url():
    database_url = os.getenv("JADE_TEST_DATABASE_URL")
    if not database_url:
        pytest.fail(
            "Defina JADE_TEST_DATABASE_URL com a URL de um banco PostgreSQL "
            "dedicado aos testes."
        )
    base_url = make_url(database_url)
    if base_url.get_backend_name() != "postgresql":
        pytest.fail("JADE_TEST_DATABASE_URL precisa apontar para PostgreSQL.")

    schema = f"jade_test_{uuid4().hex}"
    admin_engine = create_engine(database_url)
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))

    isolated_url = base_url.update_query_dict(
        {"options": [f"-csearch_path={schema}"]}
    ).render_as_string(hide_password=False)
    try:
        yield isolated_url
    finally:
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


@pytest.fixture
def session_factory(postgres_test_database_url):
    engine, factory = create_database(postgres_test_database_url)
    yield factory
    engine.dispose()


def test_selection_creates_catalog_event(session_factory):
    timestamp = datetime(2026, 11, 2, 10, tzinfo=timezone.utc)
    with session_factory() as session:
        event = process_serial_message(
            session,
            SerialMessage("S", "01", 1),
            timestamp,
        )

    assert event.message_id == "agua"
    assert event.requested_at == timestamp
    assert event.attended_at is None
    assert event.urgency == 1
    assert event.id


def test_database_rejects_non_postgresql_urls():
    with pytest.raises(ValueError, match="requer PostgreSQL"):
        create_database("sqlite://")


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql://user:password@db.example.com:5432/postgres?sslmode=require",
        "postgres://user:password@db.example.com:5432/postgres?sslmode=require",
        "postgresql+psycopg://user:password@db.example.com:5432/postgres",
    ],
)
def test_database_accepts_supabase_postgresql_urls(database_url):
    normalized_url = _normalize_database_url(database_url)

    assert normalized_url.drivername == "postgresql+psycopg"
    assert normalized_url.get_backend_name() == "postgresql"


def test_attendance_closes_oldest_pending_request_for_same_message(session_factory):
    first_time = datetime(2026, 11, 2, 10, tzinfo=timezone.utc)
    second_time = datetime(2026, 11, 2, 10, 1, tzinfo=timezone.utc)
    attended_time = datetime(2026, 11, 2, 10, 2, tzinfo=timezone.utc)
    with session_factory() as session:
        first = process_serial_message(
            session, SerialMessage("S", "01", 1), first_time
        )
        second = process_serial_message(
            session, SerialMessage("S", "01", 1), second_time
        )
        attended = process_serial_message(
            session, SerialMessage("A", "01", 1), attended_time
        )
        all_events = list(session.scalars(select(Event)))

    assert attended.id == first.id
    assert first.attended_at == attended_time
    assert second.attended_at is None
    assert len(all_events) == 2


@pytest.mark.parametrize(
    ("message", "error"),
    [
        (SerialMessage("S", "00", 1), "desconhecido"),
        (SerialMessage("S", "01", 3), "diverge"),
        (SerialMessage("A", "01", 1), "Não há solicitação pendente"),
    ],
)
def test_invalid_serial_transitions_are_rejected(session_factory, message, error):
    with session_factory() as session:
        with pytest.raises(SerialProcessingError, match=error):
            process_serial_message(session, message)
        assert list(session.scalars(select(Event))) == []


def test_events_endpoint_returns_frontend_contract(postgres_test_database_url):
    app = create_app(
        database_url=postgres_test_database_url,
        serial_enabled=False,
    )

    async def get_events():
        async with app.router.lifespan_context(app):
            factory = app.state.session_factory
            with factory() as session:
                process_serial_message(
                    session,
                    SerialMessage("S", "01", 1),
                    datetime(2026, 11, 2, 10, tzinfo=timezone.utc),
                )
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                return await client.get("/events")

    response = asyncio.run(get_events())

    assert response.status_code == 200
    result = response.json()
    assert len(result) == 1
    assert result[0] == {
        "id": result[0]["id"],
        "message_id": "agua",
        "requested_at": "2026-11-02T10:00:00+00:00",
        "attended_at": None,
    }
    assert parse_events(result).iloc[0]["message_id"] == "agua"


def test_serial_listener_persists_a_complete_frame(session_factory):
    listener = SerialListener(session_factory, "/dev/ttyUSB0", 9600)
    listener._process_frame(b"S,01,1\r\n")

    with session_factory() as session:
        events = list(session.scalars(select(Event)))

    assert len(events) == 1
    assert events[0].message_id == "agua"
