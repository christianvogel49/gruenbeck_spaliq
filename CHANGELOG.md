# Changelog

## [1.0.0] - 2026-03-02

### Added
- Initial release as a HACS custom integration (replaces the previous Docker/MQTT addon)
- Direct Modbus TCP polling via raw socket — no MQTT broker or extra infrastructure required
- 32-bit DInt decoding for operating-hour counters (registers 0–7)
- 16-bit Int decoding with scaling for analog measurements (pH, disinfection, redox, temperature)
- Bit-field decoding for status, info, alarm, and fault words (registers 16–19)
- UI config flow with connection test (host / port / unit ID / poll interval)
- Home Assistant auto-discovery via DataUpdateCoordinator
- `sensor` and `binary_sensor` platforms; alarm/fault entities use `device_class: problem`
