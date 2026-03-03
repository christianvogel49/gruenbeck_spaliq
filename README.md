# Grünbeck spaliQ — Home Assistant Integration

A custom Home Assistant integration that connects a **Grünbeck spaliQ Professional** pool treatment system directly to Home Assistant via Modbus TCP.

No MQTT broker, no Docker addon, no extra infrastructure — the integration polls the device (or its Modbus gateway) directly and exposes all measured values and status flags as HA entities.

---

## Requirements

- Home Assistant 2023.8 or newer
- A Grünbeck spaliQ Professional system with its **Modbus TCP gateway** reachable on the local network
- The gateway must accept **Function Code 0x03** (Read Holding Registers) — direct device connections using FC 0x04 are not supported

---

## Installation

### Via HACS (recommended)

1. Open HACS → **Integrations** → ⋮ → **Custom repositories**
2. Add `https://github.com/christianvogel49/gruenbeck_spaliq` as type **Integration**
3. Install **Grünbeck spaliQ** and restart Home Assistant

### Manual

Copy the `custom_components/gruenbeck_spaliq/` directory into the `custom_components/` folder of your HA config directory, then restart Home Assistant.

---

## Configuration

Go to **Settings → Devices & Services → Add Integration** and search for **Grünbeck spaliQ**.

| Field | Default | Description |
|-------|---------|-------------|
| Host | — | IP address of the Modbus gateway |
| Port | `502` | Modbus TCP port |
| Unit ID | `1` | Modbus unit / slave ID |
| Poll interval | `30` | Seconds between updates |

The config flow performs a test TCP connection before saving — if the device is unreachable you'll see a "Cannot connect" error.

---

## Entities

### Sensors

| Entity | Unit | Description |
|--------|------|-------------|
| Operating Hours System | h | Total system runtime |
| Operating Hours pH Dosing 1 | h | pH dosing pump 1 runtime |
| Operating Hours Disinfection | h | Disinfection dosing runtime |
| Operating Hours Flocculation | h | Flocculation / pH dosing 2 runtime |
| pH Value | pH | Pool water pH |
| Disinfection Value | mg/L | Disinfectant concentration |
| Redox Value | mV | Redox potential |
| Water Temperature | °C | Pool water temperature |
| Room Sensor 1 / 2 | °C | Ambient temperature sensors |

### Binary Sensors

Status flags (registers 16–17), info flags (register 18), and fault flags (register 19) are each exposed as a binary sensor. Alarm and fault entities carry `device_class: problem` so they integrate naturally with HA dashboards and alerts.

Examples: *Normalbaden aktiv*, *Hochchlorung aktiv*, *pH-Wert zu niedrig*, *Sammelstörung*, *Wartung fällig*, …

---

## Troubleshooting

**Entities show "Unavailable"**
Check the HA logs for a detailed Modbus error (connection refused, short response, exception code). Verify the gateway IP, port, and unit ID.

**Values look wrong**
Scale factors for Int16 registers are inferred from the documented value ranges. Compare the raw register dump with the device display and adjust the `scale` field in `const.py` if needed.

**Scanning the register space**

```bash
python3 test/modbus_scan.py 192.168.1.52
```

This prints every non-zero register block for both FC 3 and FC 4, with raw, signed, ÷10, and ÷100 columns — useful for verifying decoded values against the physical display.

---

## Register map

Source: Grünbeck BA_100142280000_de_084 spaliQ Professional manual.

| Register(s) | Type | Content |
|-------------|------|---------|
| 0–1 | DInt (32-bit) | Betriebsstunden Mess- & Regelanlage |
| 2–3 | DInt | Betriebsstunden pH-Dosierung 1 |
| 4–5 | DInt | Betriebsstunden Desinfektionsdosierung |
| 6–7 | DInt | Betriebsstunden Flockung/pH-Dos. 2 |
| 8 | Int16 ÷100 | pH-Wert Beckenwasser |
| 9 | Int16 ÷100 | Desinfektionswert |
| 10 | Int16 | Redox-Wert (mV) |
| 11 | Int16 ÷10 | Wassertemperatur |
| 14 | Int16 ÷10 | Raumtemperatur/Luftfeuchte 1 |
| 15 | Int16 ÷10 | Raumtemperatur/Luftfeuchte 2 |
| 16 | Bit-field | Betriebsmeldung / Anlagenstatus |
| 17 | Bit-field | Info-meldung Teil 1 |
| 18 | Bit-field | Info-meldung Teil 2 |
| 19 | Bit-field | Störmeldung Teil 1 |

---

## Contributing

Issues and pull requests are welcome at <https://github.com/christianvogel49/gruenbeck_spaliq>.

## License

MIT
