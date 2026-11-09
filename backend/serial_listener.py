"""Background reader for the configured serial device."""

import logging
from threading import Event as StopEvent
from threading import Thread

import serial
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.events import SerialProcessingError, process_serial_message
from backend.serial_protocol import SerialProtocolError, parse_serial_message

LOGGER = logging.getLogger(__name__)


class SerialListener:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        port: str,
        baudrate: int,
    ) -> None:
        if not port:
            raise ValueError("Configure JADE_SERIAL_PORT para habilitar a serial.")
        if baudrate <= 0:
            raise ValueError("JADE_SERIAL_BAUDRATE precisa ser maior que zero.")
        self._session_factory = session_factory
        self._port = port
        self._baudrate = baudrate
        self._stop_event = StopEvent()
        self._startup_event = StopEvent()
        self._startup_error: serial.SerialException | None = None
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._startup_event.clear()
        self._startup_error = None
        self._thread = Thread(
            target=self._read_frames,
            name="jade-serial-listener",
            daemon=True,
        )
        self._thread.start()
        if not self._startup_event.wait(timeout=5):
            raise RuntimeError("Tempo esgotado ao abrir a porta serial configurada.")
        if self._startup_error is not None:
            raise RuntimeError(
                f"Não foi possível abrir a porta serial {self._port}."
            ) from self._startup_error

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def _read_frames(self) -> None:
        import serial

        try:
            with serial.Serial(
                self._port,
                self._baudrate,
                bytesize=serial.SEVENBITS,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
            ) as connection:
                self._startup_event.set()
                LOGGER.info(
                    "Leitura serial iniciada em %s a %s baud.",
                    self._port,
                    self._baudrate,
                )
                while not self._stop_event.is_set():
                    frame = connection.read_until(b"\n", size=64)
                    if not frame:
                        continue
                    self._process_frame(frame)
        except serial.SerialException as exc:
            if not self._startup_event.is_set():
                self._startup_error = exc
                self._startup_event.set()
            LOGGER.exception("Falha na conexão serial %s.", self._port)

    def _process_frame(self, frame: bytes) -> None:
        try:
            message = parse_serial_message(frame)
            with self._session_factory() as session:
                event = process_serial_message(session, message)
            LOGGER.info(
                "Quadro %s aplicado ao evento %s.",
                message.message_type,
                event.id,
            )
        except (SerialProtocolError, SerialProcessingError) as exc:
            LOGGER.warning("Quadro serial rejeitado: %s", exc)
        except SQLAlchemyError:
            LOGGER.exception("Falha ao persistir quadro serial.")
