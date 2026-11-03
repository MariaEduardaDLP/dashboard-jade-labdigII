"""Testes offline para a configuração serial Jade (não acessam porta ou banco)."""

import sys
from types import SimpleNamespace

from backend.events import Event
from backend.serial_listener import SerialListener


def test_serial_listener_configures_115200_7e1(monkeypatch):
    received = {}

    class FakeSerial:
        def __init__(self, *args, **kwargs):
            received["args"] = args
            received["kwargs"] = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    fake_serial = SimpleNamespace(
        Serial=FakeSerial,
        SerialException=Exception,
        SEVENBITS=7,
        PARITY_EVEN="E",
        STOPBITS_ONE=1,
    )
    monkeypatch.setitem(sys.modules, "serial", fake_serial)

    listener = SerialListener(None, "/dev/ttyUSB0", 115200)
    listener._stop_event.set()  # Abre a porta falsa, sem entrar no laço de leitura.
    listener._read_frames()

    assert received["args"] == ("/dev/ttyUSB0", 115200)
    assert received["kwargs"] == {
        "bytesize": 7,
        "parity": "E",
        "stopbits": 1,
        "timeout": 1,
    }


def test_database_model_declares_timezone_aware_columns():
    assert Event.__table__.c.requested_at.type.timezone is True
    assert Event.__table__.c.attended_at.type.timezone is True
