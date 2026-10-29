"""Execute na raiz: streamlit run frontend/app.py."""

import os
from datetime import datetime, timedelta
from pathlib import Path
from unicodedata import normalize
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from jade.catalog import MESSAGES, TIMEZONE, URGENCIES
from jade.charts import hourly_chart, urgency_chart, usage_chart
from jade.data import DataSourceError, demo_events, fetch_api_events
from jade.metrics import (
    export_table, export_xlsx, filter_events, format_duration, hourly_counts,
    message_counts, summarize, urgency_counts,
)

ROOT = Path(__file__).resolve().parents[1]
MESSAGE_IDS = [message.id for message in MESSAGES]


@st.cache_data(ttl=60, show_spinner=False)
def load_events(source: str, api_url: str):
    if source == "demo":
        events = demo_events(datetime.now(ZoneInfo(TIMEZONE)))
    elif source == "api":
        events = fetch_api_events(api_url)
    else:
        raise DataSourceError("JADE_DATA_SOURCE deve ser demo ou api.")
    return events, datetime.now(ZoneInfo(TIMEZONE))


def toggle_hourly_message(message_id: str) -> None:
    selected = set(st.session_state.hourly_message_ids)
    if st.session_state[f"hourly_message_{message_id}"]:
        selected.add(message_id)
    else:
        selected.discard(message_id)
    st.session_state.hourly_message_ids = [item for item in MESSAGE_IDS if item in selected]


def message_filter() -> list[str]:
    # A seleção persiste mesmo quando a busca oculta e desmonta um checkbox.
    if "hourly_message_ids" not in st.session_state:
        st.session_state.hourly_message_ids = MESSAGE_IDS.copy()
    with st.popover("Filtrar mensagens", icon=":material/filter_list:", width="stretch"):
        search = st.text_input(
            "Buscar mensagem", placeholder="Digite o nome da mensagem…",
            key="hourly_message_search",
        ).strip().casefold()
        search = normalize("NFKD", search).encode("ascii", "ignore").decode()
        visible = [
            message for message in MESSAGES
            if search in normalize("NFKD", message.label.casefold()).encode("ascii", "ignore").decode()
        ]
        if not visible:
            st.caption("Nenhuma mensagem encontrada.")
        for message in visible:
            st.checkbox(
                message.label, value=message.id in st.session_state.hourly_message_ids,
                key=f"hourly_message_{message.id}", on_change=toggle_hourly_message,
                args=(message.id,),
            )
    return st.session_state.hourly_message_ids


@st.dialog("Exportar histórico")
def export_history(table: pd.DataFrame, start, end) -> None:
    st.write("Escolha o formato para baixar o histórico do período selecionado.")
    st.caption(f"{len(table)} solicitações · {start:%d/%m/%Y} a {end:%d/%m/%Y}")
    filename = f"jade-solicitacoes-{start}-{end}"
    csv, xlsx = st.columns(2)
    csv.download_button(
        "Baixar CSV", table.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{filename}.csv", mime="text/csv", icon=":material/download:",
        width="stretch", on_click="ignore",
    )
    xlsx.download_button(
        "Baixar XLSX", export_xlsx(table), file_name=f"{filename}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon=":material/download:", width="stretch", on_click="ignore",
    )


def main() -> None:
    st.set_page_config(
        page_title="Jade · Dashboard", page_icon="🦜", layout="wide",
        initial_sidebar_state="auto",
    )
    st.html(f"<style>{(ROOT / 'frontend/styles.css').read_text()}</style>")
    source = os.getenv("JADE_DATA_SOURCE", "demo").strip().lower()
    api_url = os.getenv("JADE_API_URL", "").strip()

    logo, heading = st.columns([1, 5], vertical_alignment="center")
    with logo:
        st.image(str(ROOT / "jadeLogos/principal.png"), width=140)
    with heading:
        st.html('<div class="jade-eyebrow">JADE / PAINEL DE USO</div>')
        st.title("Cada mensagem importa")
        st.markdown("Acompanhe as necessidades comunicadas e o tempo até o atendimento.")
    if source == "demo":
        st.info("Modo demonstração · Dados fictícios e mensagens de exemplo. Nenhum dado real da prancha.", icon=":material/info:")

    try:
        with st.spinner("Carregando solicitações…"):
            events, loaded_at = load_events(source, api_url)
    except DataSourceError as exc:
        st.error(str(exc), icon=":material/cloud_off:")
        if st.button("Tentar novamente", icon=":material/refresh:"):
            load_events.clear()
            st.rerun()
        st.stop()

    today = datetime.now(ZoneInfo(TIMEZONE)).date()
    earliest = min(events["requested_at"].dt.date.min(), today) if not events.empty else today
    latest = max(events["requested_at"].dt.date.max(), today) if not events.empty else today
    with st.sidebar:
        period = st.date_input(
            "Período de solicitação", value=(max(earliest, today - timedelta(days=6)), today),
            min_value=earliest, max_value=latest, format="DD/MM/YYYY",
            help="Inclui as datas inicial e final. Fuso: America/Sao_Paulo.",
        )

    if len(period) != 2:
        st.info("Selecione a data final para completar o período.")
        st.stop()
    start, end = period
    filtered = filter_events(events, start, end, list(URGENCIES), MESSAGE_IDS)
    summary = summarize(filtered)
    context, refresh = st.columns([5, 1], vertical_alignment="center")
    context.caption(
        f"{start:%d/%m/%Y} a {end:%d/%m/%Y} · "
        f"Fonte: {'demonstração' if source == 'demo' else 'API'} · "
        f"Atualizado às {loaded_at:%H:%M:%S} (São Paulo)"
    )
    if refresh.button("Atualizar dados", icon=":material/refresh:", width="stretch"):
        load_events.clear()
        st.rerun()

    cards = st.columns(4)
    cards[0].metric("Solicitações", f"{summary.total:,}".replace(",", "."))
    cards[1].metric("Atendidas", f"{summary.attended:,}".replace(",", "."))
    cards[2].metric("Sem atendimento", str(summary.pending), help="Solicitações do período sem registro do botão de atendimento.")
    cards[3].metric("Tempo médio", format_duration(summary.average_minutes), help="Tempo entre a solicitação e o botão de atendimento. Considera apenas solicitações atendidas.")

    if filtered.empty:
        st.info("Nenhuma solicitação para o período selecionado. Ajuste o período na barra lateral.")

    st.write("")
    main_chart, ranking = st.columns([3, 1.15], gap="medium")
    with main_chart, st.container(border=True):
        title, controls = st.columns([3, 1.5], vertical_alignment="center")
        title.subheader("Mensagens ao longo do dia")
        with controls:
            selected_ids = message_filter()
        st.caption(f"Total por hora no período · {len(selected_ids)} de {len(MESSAGES)} mensagens selecionadas.")
        if not selected_ids:
            st.info("Selecione ao menos uma mensagem no filtro para exibir o gráfico.")
        elif filtered.empty:
            st.caption("Sem dados para exibir neste período.")
        else:
            chart_events = filtered.loc[filtered["message_id"].isin(selected_ids)]
            st.plotly_chart(hourly_chart(hourly_counts(chart_events, selected_ids)), width="stretch", theme=None, config={"displayModeBar": False})

    counts = message_counts(filtered, MESSAGE_IDS)
    with ranking, st.container(border=True):
        st.subheader("Top 10 mensagens")
        st.caption("Mais utilizadas no período")
        ranked = counts.sort_values("count", ascending=False, kind="stable").head(10)
        rows = "".join(
            f'<li><span class="jade-rank-position">{position:02d}</span>'
            f'<span class="jade-rank-message">{row.message}</span>'
            f'<strong aria-label="{row.count} solicitações">{row.count}</strong></li>'
            for position, row in enumerate(ranked.itertuples(), start=1)
        )
        st.html(f'<ol class="jade-ranking" aria-label="Ranking de mensagens">{rows}</ol>')

    if not filtered.empty:
        usage, urgency = st.columns([3, 2], gap="medium")
        with usage, st.container(border=True):
            st.subheader("O que a prancha comunica")
            st.caption("O tamanho das bolhas representa a quantidade de solicitações. As cores indicam a urgência.")
            st.plotly_chart(usage_chart(counts), width="stretch", theme=None, config={"displayModeBar": False})
        with urgency, st.container(border=True):
            st.subheader("Níveis de urgência")
            st.caption("Distribuição das solicitações no período.")
            urgencies = urgency_counts(filtered)
            st.plotly_chart(urgency_chart(urgencies), width="stretch", theme=None, config={"displayModeBar": False})
            st.caption(" · ".join(f"{row.urgency}: {row.count}" for row in urgencies.itertuples()))

    with st.container(border=True):
        history, export = st.columns([4, 1], vertical_alignment="center")
        history.subheader("Histórico de solicitações")
        st.caption("Registros mais recentes primeiro. A exportação inclui todos os registros do período.")
        table = export_table(filtered)
        if export.button("Exportar histórico", icon=":material/download:", width="stretch"):
            export_history(table, start, end)
        st.dataframe(table, hide_index=True, width="stretch")

    with st.expander("Como ler estes indicadores"):
        st.markdown(
            "- O período considera a **data da solicitação**, no fuso de São Paulo.\n"
            "- O filtro de mensagens altera apenas o gráfico **Mensagens ao longo do dia**.\n"
            "- **Atendida** significa que o botão do acompanhante foi registrado.\n"
            "- O **tempo médio** usa apenas solicitações atendidas; sem atendimentos, aparece um traço.\n"
            "- Um atendimento após a data final ainda conta para a solicitação feita no período.\n"
            "- O gráfico por horário soma os registros de todos os dias selecionados.\n"
            "- O ranking inclui as dez mensagens em ordem de uso no período; empates seguem a ordem do catálogo.\n"
            "- As dez mensagens e suas urgências são provisórias e precisam ser confirmadas com a equipe."
        )
    st.html('<div class="jade-footer">Projeto Jade · Laboratório Digital II · Comunicação Alternativa</div>')


if __name__ == "__main__":
    main()
