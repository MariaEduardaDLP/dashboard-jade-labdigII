import pytest

from backend.events import MESSAGE_BY_CODE
from backend.serial_protocol import (
    SerialMessage,
    SerialProtocolError,
    parse_serial_message,
)


def test_serial_codes_follow_catalog_order():
    assert [MESSAGE_BY_CODE[f"{code:02d}"].id for code in range(1, 11)] == [
        "companhia",
        "descansar",
        "calor",
        "frio",
        "posicao",
        "agua",
        "comida",
        "banheiro",
        "dor",
        "ajuda",
    ]


@pytest.mark.parametrize("frame", ["S,01,3\r\n", b"S,01,3\r\n"])
def test_parse_selection_frame_preserves_leading_zero(frame):
    assert parse_serial_message(frame) == SerialMessage(
        message_type="S",
        message_code="01",
        urgency=3,
    )


def test_parse_attendance_frame():
    assert parse_serial_message("A,10,1\r\n") == SerialMessage(
        message_type="A",
        message_code="10",
        urgency=1,
    )


@pytest.mark.parametrize("frame", [
    "s,01,3\r\n",
    "S,1,3\r\n",
    "S,01,0\r\n",
    "S,01,4\r\n",
    "S,01,3\n",
    "S,01,3\r\nA,02,1\r\n",
    b"S,\xff,3\r\n",
    None,
])
def test_reject_invalid_serial_frames(frame):
    with pytest.raises(SerialProtocolError):
        parse_serial_message(frame)
