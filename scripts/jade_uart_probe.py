"""Verifica quadros UART do Jade sem conectar ao PostgreSQL.

Executar a partir da raiz do repositório:
    python -m scripts.jade_uart_probe --port /dev/ttyUSB0
"""

import argparse
from datetime import datetime, timezone

import serial
from backend.serial_protocol import SerialProtocolError, parse_serial_message


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor serial do Jade: 115200 7E1")
    parser.add_argument("--port", required=True, help="Ex.: /dev/ttyUSB0 ou /dev/serial/by-id/...")
    args = parser.parse_args()

    with serial.Serial(
        port=args.port,
        baudrate=115200,
        bytesize=serial.SEVENBITS,
        parity=serial.PARITY_EVEN,
        stopbits=serial.STOPBITS_ONE,
        timeout=1,
    ) as device:
        print(f"Escutando {args.port} em 115200 7E1 (Ctrl+C encerra)")
        while True:
            frame = device.read_until(b"\n", size=64)
            if not frame:
                continue
            now = datetime.now(timezone.utc).isoformat()
            try:
                event = parse_serial_message(frame)
            except SerialProtocolError as exc:
                print(f"{now} ERRO {frame!r} - {exc}", flush=True)
                continue
            print(
                f"{now} OK {frame!r} -> tipo={event.message_type} "
                f"codigo={event.message_code} urgencia={event.urgency}",
                flush=True,
            )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nEncerrado.")
