from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

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


def test_clearing_messages_shows_empty_state_and_recovers(app):
    app.multiselect[1].set_value([]).run()
    assert not app.exception
    assert app.metric[0].value == "0"
    assert app.metric[3].value == "—"
    assert len(app.get("plotly_chart")) == 0
    assert any("Nenhuma solicitação" in info.value for info in app.info)
    app.multiselect[1].set_value(["agua"]).run()
    assert not app.exception
    assert len(app.get("plotly_chart")) == 3
    assert app.dataframe[0].value["Mensagem"].eq("Quero água").all()


def test_api_configuration_failure_is_visible(monkeypatch):
    monkeypatch.setenv("JADE_DATA_SOURCE", "api")
    monkeypatch.delenv("JADE_API_URL", raising=False)
    app = AppTest.from_file(str(APP)).run(timeout=20)
    assert not app.exception
    assert "JADE_API_URL" in app.error[0].value
    assert not app.metric
