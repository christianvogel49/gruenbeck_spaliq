# Changelog

## [1.0.0] - 2026-03-02

### Added
- Initial release
- Modbus TCP client reading all 21 registers (0–20) in a single request
- 32-bit DInt decoding for operating-hour counters (registers 0–7)
- 16-bit Int decoding with scaling for analog measurements (pH, disinfection, redox, temperature)
- Bit-field decoding for status, info, alarm, and fault words (registers 16–20)
- MQTT publishing with Home Assistant auto-discovery (sensor + binary_sensor)
- Configurable poll interval, Modbus unit ID, and MQTT credentials via HA addon options
- Graceful shutdown on SIGTERM / SIGINT
