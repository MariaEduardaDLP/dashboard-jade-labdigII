"""Testes offline para a configuração serial Jade (não acessam porta ou banco)."""

import asyncio
import sys
from types import SimpleNamespace

import pytest

from backend.events import Event
from backend.main import create_app
from backend.serial_listener import SerialListener


def test_serial_listener_configures_115200_7e1(monkeypatch):
    received = {}

    class FakeSerial:
        def __init__(self, *args, **kwargs):
            received["args"] = args
            received["kwargs"] = kwargs

        def __enter__(self):
            listener._stop_event.set()
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
    assert {
        constraint.name for constraint in Event.__table__.constraints
    } >= {
        "uq_events_id",
        "ck_events_urgency",
        "ck_events_attendance_order",
    }


def test_serial_listener_reports_port_open_failure(monkeypatch):
    class FakeSerial:
        def __init__(self, *args, **kwargs):
            raise OSError("porta indisponível")

    fake_serial = SimpleNamespace(
        Serial=FakeSerial,
        SerialException=OSError,
        SEVENBITS=7,
        PARITY_EVEN="E",
        STOPBITS_ONE=1,
    )
    monkeypatch.setitem(sys.modules, "serial", fake_serial)
    listener = SerialListener(None, "COM99", 115200)

    with pytest.raises(RuntimeError, match="porta serial COM99"):
        listener.start()


def test_serial_listener_reconnects_after_read_disconnection(monkeypatch):
    opened = []

    class FakeConnection:
        def __init__(self, connection_number):
            self.connection_number = connection_number

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

        def read_until(self, *args, **kwargs):
            if self.connection_number == 1:
                raise OSError("adaptador desconectado")
            listener._stop_event.set()
            return b""

    class FakeSerial:
        def __init__(self, *args, **kwargs):
            opened.append((args, kwargs))
            self.connection = FakeConnection(len(opened))

        def __enter__(self):
            return self.connection.__enter__()

        def __exit__(self, exc_type, exc_val, exc_tb):
            return self.connection.__exit__(exc_type, exc_val, exc_tb)

    fake_serial = SimpleNamespace(
        Serial=FakeSerial,
        SerialException=OSError,
        SEVENBITS=7,
        PARITY_EVEN="E",
        STOPBITS_ONE=1,
    )
    monkeypatch.setitem(sys.modules, "serial", fake_serial)
    listener = SerialListener(None, "/dev/ttyUSB0", 115200)

    listener._read_frames()

    assert len(opened) == 2


@pytest.mark.parametrize("configured_baudrate", [None, ""])
def test_api_serial_listener_defaults_to_fpga_baudrate(
    monkeypatch,
    configured_baudrate,
):
    if configured_baudrate is None:
        monkeypatch.delenv("JADE_SERIAL_BAUDRATE", raising=False)
    else:
        monkeypatch.setenv("JADE_SERIAL_BAUDRATE", configured_baudrate)
    captured = {}

    class FakeEngine:
        def dispose(self):
            pass

    class FakeListener:
        def __init__(self, session_factory, port, baudrate):
            captured["port"] = port
            captured["baudrate"] = baudrate

        def start(self):
            pass

        def stop(self):
            pass

    monkeypatch.setattr(
        "backend.main.create_database",
        lambda url: (FakeEngine(), object()),
    )
    monkeypatch.setattr("backend.main.SerialListener", FakeListener)
    app = create_app(
        database_url="postgresql://localhost/jade",
        serial_enabled=True,
        serial_port="COM3",
    )

    async def run_lifespan():
        async with app.router.lifespan_context(app):
            assert captured["baudrate"] == 115200
            assert captured["port"] == "COM3"

    asyncio.run(run_lifespan())
