"""
Surplus-ack handling in GrblSerialTransport.

Regression tests for WiFi/telnet bridges that return more ``ok``
responses than commands sent (e.g. CRLF line-ending duplication):
surplus acks must be counted and must never corrupt buffer accounting.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rayforge.machine.transport import SerialTransport
from rayforge.machine.transport.grbl import GrblSerialTransport


def _make_grbl_transport():
    mock = MagicMock(spec=SerialTransport)
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.send = AsyncMock()
    mock.received = MagicMock()
    mock.status_changed = MagicMock()
    mock.is_connected = True
    mock.port = "/dev/ttyUSB0"
    return GrblSerialTransport(mock)


class TestSurplusAcks:
    @pytest.mark.asyncio
    async def test_surplus_ack_counted_and_ignored(self):
        transport = _make_grbl_transport()
        await transport.send_gcode(b"G1 X1\n", op_index=0)
        assert transport.buffer_count == 6
        assert transport.surplus_ack_count == 0

        transport.parse_incoming(b"ok\r\n")
        assert transport.buffer_count == 0
        assert transport.surplus_ack_count == 0

        transport.parse_incoming(b"ok\r\n")
        assert transport.surplus_ack_count == 1
        assert transport.buffer_count == 0

    @pytest.mark.asyncio
    async def test_double_ok_per_command(self):
        transport = _make_grbl_transport()
        for i in range(10):
            await transport.send_gcode(f"G1 X{i}\n".encode(), op_index=i)
        for _ in range(20):
            transport.parse_incoming(b"ok\r\n")
        assert transport.buffer_count == 0
        assert transport.surplus_ack_count == 10

    @pytest.mark.asyncio
    async def test_surplus_counter_reset(self):
        transport = _make_grbl_transport()
        transport.parse_incoming(b"ok\r\n")
        assert transport.surplus_ack_count == 1
        transport.reset()
        assert transport.surplus_ack_count == 0
