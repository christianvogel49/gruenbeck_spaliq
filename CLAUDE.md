# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Home Assistant addon that bridges a Grünbeck spaliQ Professional pool treatment system to MQTT via Modbus TCP. All application logic lives in `src/main.py`. The addon runs as a Docker container managed by Home Assistant.

## Development commands

Install dependencies locally (for editing/linting, not running):
```bash
pip install -r src/requirements.txt
```

**End-to-end test** (starts the addon, a fake Modbus device, and a local MQTT broker):
```bash
docker compose up --build
```

Watch MQTT output in a second terminal:
```bash
docker run --rm --network gruenbeck_spaliq_default eclipse-mosquitto:2 \
  mosquitto_sub -h mosquitto -t "gruenbeck/#" -v
```

Tear down:
```bash
docker compose down
```

`data/options.json` mirrors the keys in `config.yaml` `options:` and is what Home Assistant injects at `/data/options.json` inside the container. It is gitignored.

## Architecture

The entire bridge is one class, `ModbusBridge` in `src/main.py`, with three responsibilities:

1. **Modbus reading** — connects to the device, reads all 21 registers (0–20) in a single `read_holding_registers` call, then closes the connection. Reconnects on every poll cycle.

2. **Decoding** — three register types require different decoding:
   - Registers 0–7: 32-bit signed DInt (two consecutive 16-bit words, big-endian high-word-first) — operating hour counters.
   - Registers 8–15: 16-bit signed Int with scaling — analog sensor values (pH ÷100, temperature ÷10, etc.).
   - Registers 16–20: 16-bit bit-field words — status, info, alarm, and fault flags, published as `binary_sensor` (`ON`/`OFF`).

3. **MQTT publishing** — numeric values go to `<prefix>/sensor/<name>/state`; binary flags go to `<prefix>/binary_sensor/<name>/state`. On connect, HA auto-discovery configs are published as retained messages to `homeassistant/sensor/gruenbeck_<name>/config` and `homeassistant/binary_sensor/gruenbeck_<name>/config`.

## Register map

Defined as three module-level lists in `src/main.py`:
- `DINT_REGISTERS` — operating-hour counters (registers 0–7)
- `INT16_REGISTERS` — analog measurements (registers 8–15); each entry includes its scale divisor
- `BIT_REGISTERS` — per-bit status/alarm/fault flags (registers 16–20); `device_class="problem"` marks alarm/fault bits

Source: Grünbeck BA_100142280000_de_084_spaliQ Professional manual.

## Scaling notes

Scale factors for Int16 registers are inferred from the documented value ranges (not explicitly stated in the manual). If live values look wrong, compare raw register values to the device display and adjust the `scale` field in `INT16_REGISTERS`.

## Deploying to Home Assistant

Place this directory under `addons/gruenbeck_spaliq/` in the HA config volume, then install it as a local addon via **Settings → Add-ons → Add-on Store → ⋮ → Check for updates**.

Bump `version` in `config.yaml` for every release and add an entry to `CHANGELOG.md`.
