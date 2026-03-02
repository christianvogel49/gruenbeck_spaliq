"""Simulated Grünbeck spaliQ Professional Modbus TCP server.

Populates all 21 registers with realistic test values so the addon can be
tested end-to-end without real hardware.

Simulated state:
  - System running 12345 h, pH dosing 6789 h, disinfection 1000 h, flocculation 500 h
  - pH 7.25, disinfection 0.50 mg/L, redox 750 mV, pool temp 28.0 °C
  - Room sensors: 22.0 °C / 22.0 °C
  - Normal bathing mode active, pH dosing active
  - No alarms or faults
"""

import struct
import logging
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from pymodbus.server import StartTcpServer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def dint_words(value: int) -> tuple[int, int]:
    """Encode a 32-bit signed int as two 16-bit big-endian words (high, low)."""
    raw = struct.pack(">i", value)
    high, low = struct.unpack(">HH", raw)
    return high, low


def build_registers() -> list[int]:
    regs = [0] * 21

    # Registers 0–7: DInt operating-hour counters
    regs[0], regs[1] = dint_words(12345)   # system
    regs[2], regs[3] = dint_words(6789)    # pH dosing 1
    regs[4], regs[5] = dint_words(1000)    # disinfection
    regs[6], regs[7] = dint_words(500)     # flocculation

    # Registers 8–15: Int16 analog measurements
    regs[8]  = 725    # pH 7.25  (÷100)
    regs[9]  = 50     # disinfection 0.50 mg/L  (÷100)
    regs[10] = 750    # redox 750 mV
    regs[11] = 280    # pool temp 28.0 °C  (÷10)
    regs[12] = 0      # reserve
    regs[13] = 0      # reserve
    regs[14] = 220    # room sensor 1: 22.0 °C  (÷10)
    regs[15] = 220    # room sensor 2: 22.0 °C  (÷10)

    # Register 16: Betriebsmeldung
    #   bit 0 = status pulse ON, bit 1 = heartbeat ON
    regs[16] = 0b0000_0000_0000_0011

    # Register 17: Info-meldung Teil 1
    #   bit 0 = normal bathing active, bit 8 = pH dosing in operation
    regs[17] = 0b0000_0001_0000_0001

    # Registers 18–20: no alarms or faults
    regs[18] = 0x0000
    regs[19] = 0x0000
    regs[20] = 0x0000

    return regs


def main():
    registers = build_registers()
    log.info("Register values: %s", registers)

    block = ModbusSequentialDataBlock(0, registers)
    store = ModbusSlaveContext(hr=block)
    context = ModbusServerContext(slaves=store, single=True)

    log.info("Starting Modbus TCP simulator on 0.0.0.0:502 ...")
    StartTcpServer(context=context, address=("0.0.0.0", 502))


if __name__ == "__main__":
    main()
