"""Dados simulados e adaptador para o contrato inicial da futura API."""

from datetime import datetime, time, timedelta
from random import Random
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from jade.catalog import MESSAGES, MESSAGE_BY_ID, TIMEZONE

EVENT_COLUMNS = [
    "id", "message_id", "requested_at", "attended_at", "message", "urgency",
    "response_minutes",
]


class DataSourceError(Exception):
    """Falha de acesso ou dados incompatíveis com o contrato de eventos."""


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise DataSourceError(f"O campo {field} deve conter uma data ISO 8601 com fuso horário.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DataSourceError(f"O campo {field} contém uma data inválida.") from exc
    if parsed.tzinfo is None:
        raise DataSourceError(f"O campo {field} precisa incluir o fuso horário.")
    return parsed


def parse_events(payload: object) -> pd.DataFrame:
    """Valida a resposta inteira antes de calcular qualquer indicador."""
    if not isinstance(payload, list):
        raise DataSourceError("A API deve retornar uma lista JSON de solicitações.")
    rows = []
    seen = set()
    for event in payload:
        if not isinstance(event, dict):
            raise DataSourceError("Cada solicitação deve ser um objeto JSON.")
        event_id = event.get("id")
        message_id = event.get("message_id")
        if not isinstance(event_id, str) or not event_id.strip():
            raise DataSourceError("Cada solicitação precisa de um id textual não vazio.")
        if event_id in seen:
            raise DataSourceError("A API retornou solicitações com ids duplicados.")
        seen.add(event_id)
        if not isinstance(message_id, str) or message_id not in MESSAGE_BY_ID:
            raise DataSourceError("Uma solicitação usa message_id ausente no catálogo da prancha.")
        if "attended_at" not in event:
            raise DataSourceError("Cada solicitação precisa de attended_at, usando null se pendente.")
        requested = _timestamp(event.get("requested_at"), "requested_at")
        attended = (
            _timestamp(event["attended_at"], "attended_at")
            if event["attended_at"] is not None else None
        )
        if attended is not None and attended < requested:
            raise DataSourceError("O atendimento não pode ocorrer antes da solicitação.")
        message = MESSAGE_BY_ID[message_id]
        rows.append({
            "id": event_id,
            "message_id": message_id,
            "requested_at": requested,
            "attended_at": attended,
            "message": message.label,
            "urgency": message.urgency,
        })
    frame = pd.DataFrame(rows, columns=EVENT_COLUMNS[:-1])
    for column in ("requested_at", "attended_at"):
        frame[column] = pd.to_datetime(frame[column], utc=True).dt.tz_convert(TIMEZONE)
    frame["response_minutes"] = (
        frame["attended_at"] - frame["requested_at"]
    ).dt.total_seconds() / 60
    return frame.sort_values("requested_at", ascending=False).reset_index(drop=True)


def demo_events(now: datetime) -> pd.DataFrame:
    """Trinta dias de dados fictícios, reproduzíveis e sem eventos futuros."""
    rng = Random(42)
    local_now = now.astimezone(ZoneInfo(TIMEZONE))
    events = []
    weights = [20, 14, 9, 7, 15, 10, 6, 5, 9, 5]
    for offset in range(30):
        day = local_now.date() - timedelta(days=offset)
        for index in range(rng.randint(28, 55)):
            hour = rng.choices(range(24), weights=[1] * 6 + [5] * 16 + [1] * 2)[0]
            requested = datetime.combine(
                day, time(hour, rng.randrange(60), rng.randrange(60)),
                tzinfo=ZoneInfo(TIMEZONE),
            )
            if requested > local_now:
                continue
            message = rng.choices(MESSAGES, weights=weights)[0]
            delay = rng.randint(15, 180 if message.urgency == "Alta" else 720)
            attended = requested + timedelta(seconds=delay)
            if attended > local_now or (offset == 0 and rng.random() < 0.13):
                attended = None
            events.append({
                "id": f"demo-{day.isoformat()}-{index:03d}",
                "message_id": message.id,
                "requested_at": requested.isoformat(),
                "attended_at": attended.isoformat() if attended else None,
            })
    return parse_events(events)


def fetch_api_events(base_url: str) -> pd.DataFrame:
    """GET /events. Não substitui falhas da API por dados de demonstração."""
    if not base_url or not base_url.startswith(("http://", "https://")):
        raise DataSourceError("Configure JADE_API_URL com a URL HTTP(S) do backend.")
    try:
        response = requests.get(f"{base_url.rstrip('/')}/events", timeout=10)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise DataSourceError(
            "Não foi possível carregar as solicitações. Verifique a disponibilidade "
            "da API e o contrato de GET /events."
        ) from exc
    return parse_events(payload)
