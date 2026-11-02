"""FastAPI application consumed by the Jade dashboard."""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, field_serializer
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.database import create_database
from backend.events import Event
from backend.serial_listener import SerialListener


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    message_id: str
    requested_at: datetime
    attended_at: datetime | None

    @field_serializer("requested_at", "attended_at", when_used="json")
    def serialize_timestamp(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized not in {"true", "false", "1", "0", "yes", "no"}:
        raise ValueError(f"{name} deve ser true/false, 1/0 ou yes/no.")
    return normalized in {"true", "1", "yes"}


def create_app(
    database_url: str | None = None,
    serial_enabled: bool | None = None,
    serial_port: str | None = None,
    serial_baudrate: int | None = None,
) -> FastAPI:
    configured_database_url = database_url or os.getenv("JADE_DATABASE_URL", "")
    configured_serial_enabled = (
        serial_enabled if serial_enabled is not None else _env_bool("JADE_SERIAL_ENABLED")
    )
    configured_serial_port = serial_port or os.getenv("JADE_SERIAL_PORT", "")
    baudrate_value = serial_baudrate
    if baudrate_value is None:
        configured_baudrate = os.getenv("JADE_SERIAL_BAUDRATE", "")
        if configured_baudrate:
            try:
                baudrate_value = int(configured_baudrate)
            except ValueError as exc:
                raise ValueError("JADE_SERIAL_BAUDRATE precisa ser um número inteiro.") from exc

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        if not configured_database_url:
            raise RuntimeError("Configure JADE_DATABASE_URL para iniciar o backend.")
        engine, session_factory = create_database(configured_database_url)
        application.state.engine = engine
        application.state.session_factory = session_factory
        listener = None
        try:
            if configured_serial_enabled:
                if baudrate_value is None:
                    raise RuntimeError(
                        "Configure JADE_SERIAL_BAUDRATE para habilitar a serial."
                    )
                listener = SerialListener(
                    session_factory,
                    configured_serial_port,
                    baudrate_value,
                )
                listener.start()
            yield
        finally:
            if listener is not None:
                listener.stop()
            engine.dispose()

    application = FastAPI(
        title="Jade Backend",
        description="API de eventos da prancha de comunicação Jade.",
        version="0.1.0",
        lifespan=lifespan,
    )

    @application.get("/events", response_model=list[EventResponse])
    def list_events() -> list[Event]:
        session_factory: sessionmaker[Session] = application.state.session_factory
        with session_factory() as session:
            return list(
                session.scalars(
                    select(Event).order_by(Event.requested_at.desc(), Event.sequence.desc())
                )
            )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
