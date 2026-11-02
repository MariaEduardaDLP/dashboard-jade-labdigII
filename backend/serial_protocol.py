"""Parsing for the Jade board's serial message protocol."""

import re
from dataclasses import dataclass
from typing import Literal

MessageType = Literal["S", "A"]

_FRAME_PATTERN = re.compile(r"([SA]),([0-9]{2}),([123])\r\n")


class SerialProtocolError(ValueError):
    """A serial frame does not match the protocol."""


@dataclass(frozen=True)
class SerialMessage:
    message_type: MessageType
    message_code: str
    urgency: int


def parse_serial_message(frame: str | bytes) -> SerialMessage:
    """Parse one complete CRLF-terminated serial frame."""
    if isinstance(frame, bytes):
        try:
            frame = frame.decode("ascii")
        except UnicodeDecodeError as exc:
            raise SerialProtocolError("O quadro serial deve conter somente ASCII.") from exc
    elif not isinstance(frame, str):
        raise SerialProtocolError("O quadro serial deve ser texto ou bytes.")

    match = _FRAME_PATTERN.fullmatch(frame)
    if match is None:
        raise SerialProtocolError(
            "Quadro serial inválido; esperado S|A, dois dígitos de mensagem, "
            "urgência 1-3 e final CRLF."
        )

    message_type, message_code, urgency = match.groups()
    return SerialMessage(
        message_type=message_type,
        message_code=message_code,
        urgency=int(urgency),
    )
