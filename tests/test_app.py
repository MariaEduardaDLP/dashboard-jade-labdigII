from pathlib import Path
import json
import re

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from jade.catalog import MESSAGES

APP = Path(__file__).resolve().parents[1] / "frontend/app.py"


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("JADE_DATA_SOURCE", "demo")
    return AppTest.from_file(str(APP)).run(timeout=20)


def test_demo_renders_and_exports_the_filtered_records(app):
    assert not app.exception
    assert len(app.metric) == 4
    assert len(app.get("plotly_chart")) == 3
    total = int(app.metric[0].value.replace(".", ""))
    table = app.dataframe[0].value
    assert isinstance(table, pd.DataFrame)
    assert total == len(table)
    assert "Dados fictícios" in app.info[0].value


def test_sidebar_contains_only_period_filter(app):
    assert len(app.sidebar.date_input) == 1
    assert len(app.sidebar) == 1


def test_clearing_messages_changes_only_hourly_chart_and_recovers(app):
    total = app.metric[0].value
    table = app.dataframe[0].value.copy()
    for checkbox in app.checkbox:
        checkbox.uncheck()
    app.run()
    assert not app.exception
    assert app.metric[0].value == total
    pd.testing.assert_frame_equal(app.dataframe[0].value, table)
    assert len(app.get("plotly_chart")) == 2
    assert any("Selecione ao menos uma mensagem" in info.value for info in app.info)
    app.checkbox(key="hourly_message_agua").check().run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 3
    chart = json.loads(app.get("plotly_chart")[0].proto.spec)
    assert [trace["name"] for trace in chart["data"]] == ["Quero água"]


def test_message_search_preserves_selections_when_checkboxes_are_hidden(app):
    app.checkbox(key="hourly_message_agua").uncheck().run()
    app.text_input(key="hourly_message_search").set_value("dor").run()
    assert [checkbox.label for checkbox in app.checkbox] == ["Estou com dor"]
    app.checkbox[0].uncheck().run()
    app.text_input[0].set_value("agua").run()
    assert len(app.checkbox) == 1
    assert app.checkbox[0].label == "Quero água"
    assert not app.checkbox[0].value
    app.text_input[0].set_value("nenhuma correspondencia").run()
    assert len(app.checkbox) == 0
    app.text_input[0].set_value("").run()
    assert len(app.checkbox) == 10
    assert not app.checkbox(key="hourly_message_agua").value
    assert not app.checkbox(key="hourly_message_dor").value
    assert app.checkbox(key="hourly_message_ajuda").value


def test_export_button_opens_modal_with_both_formats(app):
    next(button for button in app.button if button.label == "Exportar histórico").click().run()
    assert not app.exception
    downloads = app.get("download_button")
    assert [button.proto.label for button in downloads] == ["Baixar CSV", "Baixar XLSX"]
    assert downloads[0].proto.url.endswith(".csv")
    assert downloads[1].proto.url.endswith(".xlsx")


def test_ranking_matches_history_counts_in_descending_order(app):
    ranking = next(element.proto.body for element in app.get("html") if 'class="jade-ranking"' in element.proto.body)
    table = app.dataframe[0].value
    counts = table["Mensagem"].value_counts()
    expected = sorted(MESSAGES, key=lambda message: -counts.get(message.label, 0))
    rows = re.findall(r'jade-rank-message">(.*?)</span><strong aria-label="(\d+) solicitações"', ranking)
    assert rows == [(message.label, str(counts.get(message.label, 0))) for message in expected]


def test_empty_api_keeps_history_and_message_filter(monkeypatch):
    from jade.data import parse_events

    monkeypatch.setenv("JADE_DATA_SOURCE", "api")
    monkeypatch.setenv("JADE_API_URL", "http://localhost:8000")
    monkeypatch.setattr("jade.data.fetch_api_events", lambda url: parse_events([]))
    empty_app = AppTest.from_file(str(APP)).run(timeout=20)
    assert not empty_app.exception
    assert empty_app.metric[0].value == "0"
    assert empty_app.metric[3].value == "—"
    assert not empty_app.get("plotly_chart")
    assert empty_app.dataframe[0].value.empty
    assert len(empty_app.checkbox) == 10
    next(button for button in empty_app.button if button.label == "Exportar histórico").click().run()
    assert not empty_app.exception
    assert len(empty_app.get("download_button")) == 2


def test_api_configuration_failure_is_visible(monkeypatch):
    monkeypatch.setenv("JADE_DATA_SOURCE", "api")
    monkeypatch.delenv("JADE_API_URL", raising=False)
    app = AppTest.from_file(str(APP)).run(timeout=20)
    assert not app.exception
    assert "JADE_API_URL" in app.error[0].value
    assert not app.metric
