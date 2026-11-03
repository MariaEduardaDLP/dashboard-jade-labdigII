"""Persist serial selections and attendance frames as dashboard events."""

from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, Index, Integer, String, select
from sqlalchemy import Index, Integer, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from backend.serial_protocol import SerialMessage
from frontend.jade.catalog import MESSAGES

URGENCY_BY_LABEL = {"Baixa": 1, "Média": 2, "Alta": 3}
MESSAGE_BY_CODE = {
    f"{index:02d}": message
    for index, message in enumerate(MESSAGES, start=1)
}


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_message_pending_fifo", "message_id", "attended_at", "sequence"),
    )

    sequence: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    message_id: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    attended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    urgency: Mapped[int] = mapped_column(Integer, nullable=False)


class SerialProcessingError(ValueError):
    """A valid serial frame cannot be applied to the current event state."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def process_serial_message(
    session: Session,
    message: SerialMessage,
    occurred_at: datetime | None = None,
) -> Event:
    """Validate a frame against the catalog and persist its event transition."""
    catalog_message = MESSAGE_BY_CODE.get(message.message_code)
    if catalog_message is None:
        raise SerialProcessingError(
            f"Código serial desconhecido: {message.message_code}."
        )

    expected_urgency = URGENCY_BY_LABEL[catalog_message.urgency]
    if message.urgency != expected_urgency:
        raise SerialProcessingError(
            f"A urgência serial do código {message.message_code} diverge do catálogo."
        )

    event_time = occurred_at or _utc_now()
    if event_time.tzinfo is None:
        raise SerialProcessingError("O horário do quadro precisa incluir fuso horário.")
    event_time = event_time.astimezone(timezone.utc)

    with session.begin():
        if message.message_type == "S":
            event = Event(
                id=str(uuid4()),
                message_id=catalog_message.id,
                requested_at=event_time,
                attended_at=None,
                urgency=message.urgency,
            )
            session.add(event)
        else:
            event = session.scalar(
                select(Event)
                .where(
                    Event.message_id == catalog_message.id,
                    Event.attended_at.is_(None),
                )
                .order_by(Event.requested_at.asc(), Event.sequence.asc())
                .limit(1)
                .with_for_update()
            )
            if event is None:
                raise SerialProcessingError(
                    f"Não há solicitação pendente para a mensagem "
                    f"{message.message_code}."
                )
            requested_at = event.requested_at
            if requested_at.tzinfo is None:
                requested_at = requested_at.replace(tzinfo=timezone.utc)
            if event_time < requested_at:
                raise SerialProcessingError(
                    "O atendimento não pode ocorrer antes da solicitação."
                )
            event.attended_at = event_time

    return event
