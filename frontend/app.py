"""Execute na raiz: streamlit run frontend/app.py."""

import os
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

from jade.catalog import MESSAGES, TIMEZONE, URGENCIES
from jade.charts import hourly_chart, urgency_chart, usage_chart
from jade.data import DataSourceError, demo_events, fetch_api_events
from jade.metrics import (
    export_table, filter_events, format_duration, hourly_counts, message_counts,
    summarize, urgency_counts,
)

ROOT = Path(__file__).resolve().parents[1]


@st.cache_data(ttl=60, show_spinner=False)
def load_events(source: str, api_url: str):
    if source == "demo":
        events = demo_events(datetime.now(ZoneInfo(TIMEZONE)))
    elif source == "api":
        events = fetch_api_events(api_url)
    else:
        raise DataSourceError("JADE_DATA_SOURCE deve ser demo ou api.")
    return events, datetime.now(ZoneInfo(TIMEZONE))


def main() -> None:
    st.set_page_config(
        page_title="Jade · Dashboard", page_icon="🦜", layout="wide",
        initial_sidebar_state="auto",
    )
    st.html(f"<style>{(ROOT / 'frontend/styles.css').read_text()}</style>")
    source = os.getenv("JADE_DATA_SOURCE", "demo").strip().lower()
    api_url = os.getenv("JADE_API_URL", "").strip()

    with st.sidebar:
        st.image(str(ROOT / "jadeLogos/selo.png"), width=150)
        st.markdown("### Projeto Jade")
        st.caption("Comunicação que aproxima.\n\nDashboard da prancha de Comunicação Alternativa.")
        st.divider()
        st.markdown("**Explorar os dados**")
        if st.button("Atualizar dados", width="stretch", icon=":material/refresh:"):
            load_events.clear()

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
        st.caption("Use Atualizar dados na barra lateral depois de corrigir a configuração ou o serviço.")
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
        urgencies = st.multiselect("Níveis de urgência", URGENCIES, default=URGENCIES)
        message_ids = st.multiselect(
            "Mensagens", [message.id for message in MESSAGES],
            default=[message.id for message in MESSAGES],
            format_func=lambda message_id: next(m.label for m in MESSAGES if m.id == message_id),
        )
        st.divider()
        st.caption(f"Fonte: {'demonstração' if source == 'demo' else 'API'}")
        st.caption(f"Carregado em {loaded_at:%d/%m/%Y às %H:%M:%S}\n\nFuso: São Paulo (America/Sao_Paulo).")

    if len(period) != 2:
        st.info("Selecione a data final para completar o período.")
        st.stop()
    start, end = period
    selected_ids = [m.id for m in MESSAGES if m.id in message_ids and m.urgency in urgencies]
    filtered = filter_events(events, start, end, urgencies, selected_ids)
    summary = summarize(filtered)
    st.caption(f"{start:%d/%m/%Y} a {end:%d/%m/%Y} · {len(selected_ids)} mensagens selecionadas")

    cards = st.columns(4)
    cards[0].metric("Solicitações", f"{summary.total:,}".replace(",", "."))
    cards[1].metric("Atendidas", f"{summary.attended:,}".replace(",", "."))
    cards[2].metric("Sem atendimento", str(summary.pending), help="Solicitações do período sem registro do botão de atendimento.")
    cards[3].metric("Tempo médio", format_duration(summary.average_minutes), help="Tempo entre a solicitação e o botão de atendimento. Considera apenas solicitações atendidas.")

    if filtered.empty:
        st.info("Nenhuma solicitação para os filtros selecionados. Ajuste o período, as urgências ou as mensagens.")
    else:
        st.write("")
        with st.container(border=True):
            st.subheader("Mensagens ao longo do dia")
            st.caption("Total por hora no período selecionado. Toque na legenda para destacar ou ocultar mensagens.")
            st.plotly_chart(hourly_chart(hourly_counts(filtered, selected_ids)), width="stretch", theme=None, config={"displayModeBar": False})

        usage, urgency = st.columns([3, 2], gap="medium")
        with usage, st.container(border=True):
            st.subheader("O que a prancha comunica")
            st.caption("Quantidade de solicitações por mensagem. As cores indicam a urgência.")
            st.plotly_chart(usage_chart(message_counts(filtered, selected_ids)), width="stretch", theme=None, config={"displayModeBar": False})
        with urgency, st.container(border=True):
            st.subheader("Níveis de urgência")
            st.caption("Distribuição das solicitações no período.")
            counts = urgency_counts(filtered)
            st.plotly_chart(urgency_chart(counts), width="stretch", theme=None, config={"displayModeBar": False})
            st.caption(" · ".join(f"{row.urgency}: {row.count}" for row in counts.itertuples()))

        with st.container(border=True):
            st.subheader("Histórico de solicitações")
            st.caption("Registros mais recentes primeiro. A exportação inclui todos os registros filtrados.")
            table = export_table(filtered)
            st.download_button(
                "Exportar CSV", table.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"jade-solicitacoes-{start}-{end}.csv", mime="text/csv",
                icon=":material/download:",
            )
            st.dataframe(table, hide_index=True, width="stretch")

    with st.expander("Como ler estes indicadores"):
        st.markdown(
            "- O período considera a **data da solicitação**, no fuso de São Paulo.\n"
            "- **Atendida** significa que o botão do acompanhante foi registrado.\n"
            "- O **tempo médio** usa apenas solicitações atendidas; sem atendimentos, aparece um traço.\n"
            "- Um atendimento após a data final ainda conta para a solicitação feita no período.\n"
            "- O gráfico por horário soma os registros de todos os dias selecionados.\n"
            "- As dez mensagens e suas urgências são provisórias e precisam ser confirmadas com a equipe."
        )
    st.html('<div class="jade-footer">Projeto Jade · Laboratório Digital II · Comunicação Alternativa</div>')


if __name__ == "__main__":
    main()
