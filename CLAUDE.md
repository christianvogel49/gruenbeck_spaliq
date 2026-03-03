# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant custom integration (HACS-compatible) that connects a Grünbeck spaliQ Professional pool treatment system directly to Home Assistant via Modbus TCP — no MQTT broker, no Docker addon required.

## Repository layout

```
custom_components/gruenbeck_spaliq/   # The HA integration
  __init__.py       — entry point: sets up coordinator + platforms
  config_flow.py    — UI config flow (host / port / unit_id / poll_interval)
  coordinator.py    — GruenbeckCoordinator (DataUpdateCoordinator), raw socket Modbus read
  const.py          — DOMAIN, register lists (DINT / INT16 / BIT), decode helpers
  sensor.py         — CoordinatorEntity subclasses for analog values
  binary_sensor.py  — CoordinatorEntity subclasses for bit-field flags
  manifest.json     — integration metadata
  translations/     — UI strings
test/
  modbus_scan.py    — standalone scanner: tries func=3/4 across all register blocks
  modbus_simulator.py — fake Modbus device for offline development
```

## Modbus connection

- Connect via the **Modbus gateway** (e.g. 192.168.1.52), port 502, unit_id 1.
- Use **function code 0x03** (Read Holding Registers) — the gateway requires this.
- Read registers 0–20 in a single request (count = 21).
- The integration uses a raw TCP socket instead of pymodbus because the gateway returns
  a non-standard MBAP header and an extra trailing byte that pymodbus rejects.
- Do **not** connect directly to the device IP (192.168.1.123) — it uses func=4 with
  non-standard encoding and its func=3 returns exception 0x02.

## Register decoding

Three register types, defined as module-level lists in `const.py`:

| List | Registers | Type | Decode |
|------|-----------|------|--------|
| `DINT_REGISTERS` | 0–7 | 32-bit signed DInt (operating-hour counters) | `decode_dint(high_word, low_word)` — big-endian, high word first |
| `INT16_REGISTERS` | 8–15 | 16-bit signed Int with scaling | `decode_int16(raw) / scale` |
| `BIT_REGISTERS` | 16–19 | Per-bit flags (status / info / alarm / fault) | `get_bit(reg_word, bit)` → `binary_sensor` |

Register 20 (Störmeldung Teil 2) returns exception 0x02 on real hardware — it is not read.

## Development

Install dependencies for linting (the integration itself has no Python requirements outside HA):
```bash
pip install homeassistant voluptuous
```

Run the Modbus scanner against a live device:
```bash
python3 test/modbus_scan.py 192.168.1.52
```

Run a local fake device for offline testing:
```bash
python3 test/modbus_simulator.py
```

## Deploying to Home Assistant

Copy `custom_components/gruenbeck_spaliq/` into the `custom_components/` directory of your
HA config volume, then restart Home Assistant and add the integration via
**Settings → Devices & Services → Add Integration → Grünbeck spaliQ**.

For HACS: add this repository as a custom repository (type: Integration), then install
and restart HA.

Bump `version` in `manifest.json` for every release and add an entry to `CHANGELOG.md`.
