import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from backend.events import (
    Base,
    Event,
    MESSAGE_BY_CODE,
    SerialProcessingError,
    process_serial_message,
)
from backend.serial_protocol import SerialMessage
from backend.main import create_app
from frontend.jade.data import parse_events
from frontend.jade.metrics import message_counts, summarize


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield factory
    engine.dispose()


def _api_payload(events):
    def iso_timestamp(value):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    return [
        {
            "id": event.id,
            "message_id": event.message_id,
            "requested_at": iso_timestamp(event.requested_at),
            "attended_at": (
                iso_timestamp(event.attended_at) if event.attended_at else None
            ),
        }
        for event in events
    ]


def _process(session_factory, message, occurred_at):
    with session_factory() as session:
        return process_serial_message(session, message, occurred_at)


def test_ten_message_cycles_persist_once_and_match_dashboard_catalog(session_factory):
    start = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)

    for index in range(1, 11):
        code = f"{index:02d}"
        message = MESSAGE_BY_CODE[code]
        urgency = {"Baixa": 1, "Média": 2, "Alta": 3}[message.urgency]
        requested_at = start + timedelta(minutes=index)
        _process(
            session_factory,
            SerialMessage("S", code, urgency),
            requested_at,
        )
        _process(
            session_factory,
            SerialMessage("A", code, urgency),
            requested_at + timedelta(seconds=index),
        )

    with session_factory() as session:
        records = list(session.scalars(select(Event).order_by(Event.sequence)))

    assert len(records) == 10
    assert len({event.id for event in records}) == 10
    assert all(event.attended_at is not None for event in records)
    assert [event.message_id for event in records] == [
        MESSAGE_BY_CODE[f"{index:02d}"].id for index in range(1, 11)
    ]
    assert [event.urgency for event in records] == [
        {"Baixa": 1, "Média": 2, "Alta": 3}[
            MESSAGE_BY_CODE[f"{index:02d}"].urgency
        ]
        for index in range(1, 11)
    ]

    dashboard_events = parse_events(_api_payload(records))
    summary = summarize(dashboard_events)
    counts = message_counts(
        dashboard_events,
        [MESSAGE_BY_CODE[f"{index:02d}"].id for index in range(1, 11)],
    )
    assert (summary.total, summary.attended) == (10, 10)
    assert summary.average_minutes == pytest.approx(5.5 / 60)
    assert counts["count"].tolist() == [1] * 10
    assert dashboard_events["response_minutes"].sum() == pytest.approx(55 / 60)


def test_message_05_response_metrics_use_recorded_timestamps(session_factory):
    start = datetime(2026, 11, 17, 13, tzinfo=timezone.utc)
    urgency = 2

    for index, seconds in enumerate((1, 5, 10)):
        requested_at = start + timedelta(minutes=index)
        _process(
            session_factory,
            SerialMessage("S", "05", urgency),
            requested_at,
        )
        _process(
            session_factory,
            SerialMessage("A", "05", urgency),
            requested_at + timedelta(seconds=seconds),
        )

    with session_factory() as session:
        records = list(session.scalars(select(Event).order_by(Event.sequence)))

    dashboard_events = parse_events(_api_payload(records))
    assert dashboard_events["response_minutes"].tolist() == pytest.approx(
        [10 / 60, 5 / 60, 1 / 60]
    )
    assert summarize(dashboard_events).average_minutes == pytest.approx(16 / 180)


def test_unmatched_attendance_is_rejected_and_newest_pending_is_closed(session_factory):
    timestamp = datetime(2026, 11, 17, 14, tzinfo=timezone.utc)
    with session_factory() as session:
        with pytest.raises(SerialProcessingError, match="Não há solicitação pendente"):
            process_serial_message(session, SerialMessage("A", "01", 1), timestamp)

        first = process_serial_message(
            session, SerialMessage("S", "01", 1), timestamp
        )
        second = process_serial_message(
            session, SerialMessage("S", "01", 1), timestamp + timedelta(seconds=1)
        )
        attended = process_serial_message(
            session, SerialMessage("A", "01", 1), timestamp + timedelta(seconds=2)
        )
        records = list(session.scalars(select(Event).order_by(Event.sequence)))

    assert attended.id == second.id
    assert second.attended_at == timestamp + timedelta(seconds=2)
    assert first.attended_at is None
    assert len(records) == 2


@pytest.mark.parametrize(
    ("message", "error"),
    [
        (SerialMessage("S", "00", 1), "desconhecido"),
        (SerialMessage("S", "01", 3), "diverge"),
    ],
)
def test_unknown_message_and_mismatched_urgency_are_not_persisted(
    session_factory,
    message,
    error,
):
    with session_factory() as session:
        with pytest.raises(SerialProcessingError, match=error):
            process_serial_message(
                session,
                message,
                datetime(2026, 11, 17, 14, tzinfo=timezone.utc),
            )
        assert list(session.scalars(select(Event))) == []


def test_api_exposes_persisted_events_in_dashboard_contract(
    monkeypatch,
    session_factory,
):
    engine = session_factory.kw["bind"]
    monkeypatch.setattr(
        "backend.main.create_database",
        lambda database_url: (engine, session_factory),
    )
    app = create_app(
        database_url="postgresql://test/jade",
        serial_enabled=False,
    )

    async def get_events():
        async with app.router.lifespan_context(app):
            requested_at = datetime(2026, 11, 17, 15, tzinfo=timezone.utc)
            _process(
                session_factory,
                SerialMessage("S", "06", 2),
                requested_at,
            )
            _process(
                session_factory,
                SerialMessage("A", "06", 2),
                requested_at + timedelta(seconds=5),
            )
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                return await client.get("/events")

    response = asyncio.run(get_events())

    assert response.status_code == 200
    dashboard_events = parse_events(response.json())
    assert len(dashboard_events) == 1
    assert dashboard_events.iloc[0]["message_id"] == "agua"
    assert dashboard_events.iloc[0]["response_minutes"] == pytest.approx(5 / 60)
