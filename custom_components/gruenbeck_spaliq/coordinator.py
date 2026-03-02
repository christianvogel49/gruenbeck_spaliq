"""DataUpdateCoordinator for Grünbeck spaliQ."""
import logging
import socket
import struct
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    BIT_REGISTERS,
    DINT_REGISTERS,
    INT16_REGISTERS,
    decode_dint,
    decode_int16,
    get_bit,
)

_LOGGER = logging.getLogger(__name__)


class GruenbeckCoordinator(DataUpdateCoordinator):
    """Polls Modbus registers and decodes them into a flat dict."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        unit_id: int,
        poll_interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=poll_interval),
        )
        self._host = host
        self._port = port
        self._unit_id = unit_id

    async def _async_update_data(self) -> dict:
        try:
            regs = await self.hass.async_add_executor_job(self._read_registers)
        except UpdateFailed:
            raise
        except Exception as exc:
            raise UpdateFailed(f"Unexpected error reading Modbus registers: {exc}") from exc
        return self._decode(regs)

    def _read_registers(self) -> list[int]:
        """Read registers 0–20 via raw TCP socket.

        The device returns a valid Modbus TCP response but with a non-standard
        Protocol Identifier in the MBAP header and one extra trailing byte,
        both of which cause pymodbus to reject the frame.  We build the request
        ourselves and parse register data from bytes 9–50 of the response.
        """
        count = 20
        start = 0
        func = 4  # 0x04 = Read Input Registers (sensor/measurement data is read-only)
        # Standard Modbus TCP request (12 bytes):
        #   MBAP: trans_id=1, proto_id=0, length=6
        #   PDU:  unit_id, func, start_addr, quantity
        request = struct.pack(">HHHBBHH", 1, 0, 6, self._unit_id, func, start, count)

        try:
            with socket.create_connection((self._host, self._port), timeout=10) as sock:
                sock.sendall(request)
                data = b""
                sock.settimeout(5)
                try:
                    while len(data) < 9 + count * 2:
                        chunk = sock.recv(256)
                        if not chunk:
                            break
                        data += chunk
                except OSError:
                    pass
        except OSError as exc:
            raise UpdateFailed(
                f"Cannot connect to Modbus device at {self._host}:{self._port} — {exc}"
            ) from exc

        _LOGGER.debug("Raw Modbus response (%d bytes): %s", len(data), data.hex())

        # A Modbus exception response is exactly 9 bytes — check before the length guard.
        if len(data) >= 9 and data[7] & 0x80:
            raise UpdateFailed(
                f"Modbus exception from device: func=0x{data[7]:02x}, "
                f"exception_code=0x{data[8]:02x} (raw: {data.hex()})"
            )

        expected = 9 + count * 2  # 51 bytes
        if len(data) < expected:
            raise UpdateFailed(
                f"Short response from device: {len(data)} bytes (expected {expected}) "
                f"(raw: {data.hex()})"
            )

        func_code = data[7]
        if func_code not in (0x03, 0x04):
            raise UpdateFailed(f"Unexpected function code: 0x{func_code:02x}")

        regs_raw = data[9 : 9 + count * 2]
        return [struct.unpack(">H", regs_raw[i * 2 : i * 2 + 2])[0] for i in range(count)]

    def _decode(self, regs: list[int]) -> dict:
        result: dict = {}

        for _label, key, start in DINT_REGISTERS:
            result[key] = decode_dint(regs[start], regs[start + 1])

        for _label, key, reg, scale, _unit, _dc in INT16_REGISTERS:
            raw = decode_int16(regs[reg])
            result[key] = raw / scale if scale != 1 else raw

        for reg, bit, key, _label, _dc in BIT_REGISTERS:
            result[key] = get_bit(regs[reg], bit)

        return result
