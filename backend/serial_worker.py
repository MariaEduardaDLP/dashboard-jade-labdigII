"""Run the serial collector locally without exposing an HTTP API."""

import logging
import os
from pathlib import Path
import time

from dotenv import load_dotenv
from serial.tools import list_ports
from sqlalchemy.exc import SQLAlchemyError

from backend.database import create_database
from backend.serial_listener import SerialListener

LOGGER = logging.getLogger("jade_serial_worker")
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _serial_port() -> str:
    configured_port = os.getenv("JADE_SERIAL_PORT", "").strip()
    if configured_port:
        return configured_port

    ports = [port.device for port in list_ports.comports()]
    if ports:
        print(f"Portas detectadas: {', '.join(ports)}")
    else:
        print("Nenhuma porta serial foi detectada.")
    port = input("Digite a porta da prancha (por exemplo, COM3): ").strip()
    if not port:
        raise ValueError("A porta serial é obrigatória para iniciar o coletor.")
    return port


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    database_url = os.getenv("JADE_DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "JADE_DATABASE_URL não está configurada. Preencha o arquivo .env "
            "na pasta do projeto."
        )

    try:
        baudrate = int(os.getenv("JADE_SERIAL_BAUDRATE", "115200"))
    except ValueError as exc:
        raise ValueError("JADE_SERIAL_BAUDRATE precisa ser um número inteiro.") from exc

    engine = None
    listener = None
    try:
        engine, session_factory = create_database(database_url)
        port = _serial_port()
        listener = SerialListener(session_factory, port, baudrate)
        listener.start()
        print(
            f"Coletor ativo em {port}, {baudrate} baud, 7E1. "
            "Deixe esta janela aberta; Ctrl+C encerra."
        )
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nColetor encerrado.")
    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Não foi possível acessar o PostgreSQL do Supabase. Confira "
            "JADE_DATABASE_URL e a conexão com a internet."
        ) from exc
    finally:
        if listener is not None:
            listener.stop()
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    main()
