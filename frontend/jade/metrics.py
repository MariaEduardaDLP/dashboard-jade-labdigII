"""Regras das métricas, independentes da interface Streamlit."""

from dataclasses import dataclass
from datetime import date

import pandas as pd

from jade.catalog import MESSAGES, URGENCIES


@dataclass(frozen=True)
class Summary:
    total: int
    attended: int
    pending: int
    average_minutes: float | None


def filter_events(
    events: pd.DataFrame,
    start: date,
    end: date,
    urgencies: list[str],
    message_ids: list[str],
) -> pd.DataFrame:
    dates = events["requested_at"].dt.date
    return events.loc[
        dates.between(start, end)
        & events["urgency"].isin(urgencies)
        & events["message_id"].isin(message_ids)
    ].copy()


def summarize(events: pd.DataFrame) -> Summary:
    attended = int(events["attended_at"].notna().sum())
    return Summary(
        total=len(events),
        attended=attended,
        pending=len(events) - attended,
        average_minutes=float(events["response_minutes"].mean()) if attended else None,
    )


def hourly_counts(events: pd.DataFrame, message_ids: list[str]) -> pd.DataFrame:
    """Inclui as 24 horas e mensagens sem uso, mesmo em períodos de vários dias."""
    index = pd.MultiIndex.from_product([message_ids, range(24)], names=["message_id", "hour"])
    counts = events.groupby(["message_id", events["requested_at"].dt.hour.rename("hour")]).size()
    result = counts.reindex(index, fill_value=0).rename("count").reset_index()
    labels = {message.id: message.label for message in MESSAGES}
    result["message"] = result["message_id"].map(labels)
    return result


def message_counts(events: pd.DataFrame, message_ids: list[str]) -> pd.DataFrame:
    counts = events.groupby("message_id").size()
    return pd.DataFrame([
        {"message": message.label, "urgency": message.urgency,
         "count": int(counts.get(message.id, 0))}
        for message in MESSAGES if message.id in message_ids
    ], columns=["message", "urgency", "count"])


def urgency_counts(events: pd.DataFrame) -> pd.DataFrame:
    return (events.groupby("urgency").size().reindex(URGENCIES, fill_value=0)
            .rename("count").rename_axis("urgency").reset_index())


def format_duration(minutes: float | None) -> str:
    if minutes is None:
        return "—"
    seconds = round(minutes * 60)
    hours, remainder = divmod(seconds, 3600)
    whole_minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours} h {whole_minutes:02d} min"
    if whole_minutes:
        return f"{whole_minutes} min {seconds:02d} s"
    return f"{seconds} s"


def export_table(events: pd.DataFrame) -> pd.DataFrame:
    """Usa datas com offset também no CSV, preservando o fuso do evento."""
    result = events[["id", "message", "urgency", "requested_at", "attended_at"]].copy()
    result["status"] = events["attended_at"].notna().map({True: "Atendida", False: "Pendente"})
    result["response_minutes"] = events["response_minutes"].round(2)
    for column in ("requested_at", "attended_at"):
        result[column] = result[column].map(lambda value: value.isoformat() if pd.notna(value) else "")
    return result.rename(columns={
        "id": "Solicitação", "message": "Mensagem", "urgency": "Urgência",
        "requested_at": "Solicitada em", "attended_at": "Atendida em",
        "status": "Status", "response_minutes": "Tempo de atendimento (min)",
    })
