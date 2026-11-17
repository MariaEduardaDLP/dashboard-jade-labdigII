import pytest

from backend.events import MESSAGE_BY_CODE
from backend.serial_protocol import (
    SerialMessage,
    SerialProtocolError,
    parse_serial_message,
)
from shared.catalog import MESSAGES


def test_message_catalog_order_and_urgencies_follow_fpga_codes():
    expected_ids = [
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
    assert [message.id for message in MESSAGES] == expected_ids
    assert [MESSAGE_BY_CODE[f"{code:02d}"].id for code in range(1, 11)] == expected_ids
    assert [message.urgency for message in MESSAGES] == [
        "Baixa", "Baixa", "Baixa", "Baixa",
        "Média", "Média", "Média", "Média",
        "Alta", "Alta",
    ]
    assert MESSAGES[-1].label == "Preciso de ajuda"


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
