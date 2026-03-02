"""Grünbeck spaliQ Professional Modbus Bridge.

Reads all 21 registers (0–20) from the device in a single Modbus TCP request
and publishes each value as an MQTT sensor with Home Assistant auto-discovery.

Register map (from BA_100142280000_de_084_spaliQ Professional):
  0– 1  DInt (32-bit)  Betriebsstunden Mess- und Regelanlage           h
  2– 3  DInt (32-bit)  Betriebsstunden pH-Dosierung 1                  h
  4– 5  DInt (32-bit)  Betriebsstunden Desinfektionsdosierung           h
  6– 7  DInt (32-bit)  Betriebsstunden Flockungsdosierung/pH-Dos. 2    h
  8     Int  (16-bit)  pH-Wert Beckenwasser          0.00–14.00         pH   (÷100)
  9     Int  (16-bit)  Desinfektionswert Beckenwasser 0.00–10.00        mg/l (÷100)
 10     Int  (16-bit)  Redox-Wert Beckenwasser        0–1300            mV
 11     Int  (16-bit)  Wassertemperatur Becken         0.0–50.0         °C   (÷10)
 12     Int  (16-bit)  Reserve
 13     Int  (16-bit)  Reserve
 14     Int  (16-bit)  Raumtemperatur / Luftfeuchte (config-dependent)
 15     Int  (16-bit)  Raumtemperatur / Luftfeuchte (config-dependent)
 16     Word (16-bit)  Betriebsmeldung / Lebensbit      (bit flags)
 17     Word (16-bit)  Info-meldung Teil 1              (bit flags)
 18     Word (16-bit)  Info-meldung Teil 2              (bit flags)
 19     Word (16-bit)  Störmeldung Teil 1               (bit flags)
 20     Word (16-bit)  Störmeldung Teil 2 (reserved)    (bit flags)

NOTE: The DInt registers use big-endian word order (high word first).
      Scaling factors for Int16 registers are inferred from the documented
      value ranges — verify against the actual device if values look wrong.
"""

import json
import logging
import signal
import socket
import struct
import sys
import time

import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

OPTIONS_FILE = "/data/options.json"

# ---------------------------------------------------------------------------
# Register layout
# ---------------------------------------------------------------------------

# 32-bit operating-hour counters (DInt, high word first).
# Each entry: (friendly_name, mqtt_name, start_register)
DINT_REGISTERS = [
    ("Betriebsstunden Mess- und Regelanlage",        "operating_hours_system",        0),
    ("Betriebsstunden pH-Dosierung 1",               "operating_hours_ph_dosing_1",   2),
    ("Betriebsstunden Desinfektionsdosierung",        "operating_hours_disinfection",  4),
    ("Betriebsstunden Flockungsdosierung/pH-Dos. 2", "operating_hours_flocculation",  6),
]

# 16-bit analog measurements.
# Each entry: (friendly_name, mqtt_name, register, scale, unit, ha_device_class)
#   scale:  divide raw integer by this value to get the physical value
INT16_REGISTERS = [
    ("pH-Wert Beckenwasser",       "ph_value",          8,  100, "pH",   None),
    ("Desinfektionswert",          "disinfection_value", 9,  100, "mg/L", None),
    ("Redox-Wert",                 "redox_value",        10,   1, "mV",   None),
    ("Wassertemperatur",           "water_temperature",  11,  10, "°C",   "temperature"),
    ("Raumtemperatur/Luftfeuchte", "room_sensor_1",      14,  10, "°C",   "temperature"),
    ("Raumtemperatur/Luftfeuchte", "room_sensor_2",      15,  10, "°C",   "temperature"),
]

# Bit-field status/alarm/fault words.
# Each entry: (register, bit, mqtt_name, friendly_name, ha_device_class)
#   ha_device_class: "problem" for alarms/faults, None for info bits
BIT_REGISTERS = [
    # Register 16 – Betriebsmeldung / Anlagenstatus
    (16,  0, "status_pulse",               "Status Puls",                   None),
    (16,  1, "heartbeat",                  "Lebensbit (Anlagenstatus)",      None),

    # Register 17 – Info-meldung Teil 1
    (17,  0, "mode_normal_bathing",        "Normalbaden aktiv",              None),
    (17,  2, "mode_superchlorination",     "Hochchlorung aktiv",             None),
    (17,  3, "mode_economy",               "Sparbetrieb aktiv",              None),
    (17,  4, "mode_part_load",             "Teillastbetrieb aktiv",          None),
    (17,  5, "req_superchlorination",      "Hochchlorung angefordert",       None),
    (17,  6, "req_economy",                "Sparbetrieb angefordert",        None),
    (17,  7, "req_part_load",              "Teillastbetrieb angefordert",    None),
    (17,  8, "dosing_ph_1",               "pH-Dosierung 1 in Betrieb",      None),
    (17,  9, "dosing_disinfection",        "Desinfektionsdosierung",         None),
    (17, 10, "dosing_flocculation",        "Flockungsdosierung/pH-Dos. 2",   None),
    (17, 11, "heating",                    "Heizung",                        None),
    (17, 14, "collective_message_1",       "Sammelmeldung 1",                "problem"),
    (17, 15, "collective_message_2",       "Sammelmeldung 2",                "problem"),

    # Register 18 – Info-meldung Teil 2
    (18,  0, "info_maintenance",           "Wartung fällig",                 "problem"),
    (18,  1, "alarm_ph_low",               "pH-Wert zu niedrig",             "problem"),
    (18,  2, "alarm_ph_high",              "pH-Wert zu hoch",                "problem"),
    (18,  3, "alarm_disinfection_low",     "Desinfektion zu niedrig",        "problem"),
    (18,  4, "alarm_disinfection_high",    "Desinfektion zu hoch",           "problem"),
    (18,  5, "alarm_redox_low",            "Redox-Wert zu niedrig",          "problem"),
    (18,  6, "alarm_redox_high",           "Redox-Wert zu hoch",             "problem"),
    (18, 10, "alarm_no_flow_measurement",  "Kein Durchfluss Messwasser",     "problem"),
    (18, 11, "alarm_no_flow_filtrate",     "Kein Durchfluss Filtrat",        "problem"),
    (18, 12, "alarm_refill_ph_1",          "Dosierbehälter pH-Dos. 1 leer",  "problem"),
    (18, 13, "alarm_refill_disinfection",  "Dosierbehälter Desinf. leer",    "problem"),
    (18, 14, "alarm_refill_flocculation",  "Dosierbehälter Flockung leer",   "problem"),

    # Register 19 – Störmeldung Teil 1
    (19,  0, "fault_collective",           "Sammelstörung",                  "problem"),
    (19,  1, "fault_ph_dosing_1",          "Störung pH-Dosierung 1",         "problem"),
    (19,  2, "fault_disinfection",         "Störung Desinfektionsdosierung", "problem"),
    (19,  3, "fault_flocculation",         "Störung Flockungsdosierung",     "problem"),
    (19,  4, "fault_container_ph_1",       "Störung Behälter pH-Dos. 1",     "problem"),
    (19,  5, "fault_container_disinfect",  "Störung Behälter Desinfektion",  "problem"),
    (19,  6, "fault_container_flocc",      "Störung Behälter Flockung",      "problem"),
    (19,  7, "fault_temperature_sensor",   "Störung Temperatursensor",       "problem"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_options() -> dict:
    with open(OPTIONS_FILE) as f:
        return json.load(f)


def decode_dint(high_word: int, low_word: int) -> int:
    """Combine two 16-bit Modbus registers into a signed 32-bit integer."""
    raw = struct.pack(">HH", high_word, low_word)
    return struct.unpack(">i", raw)[0]


def decode_int16(word: int) -> int:
    """Reinterpret a 16-bit Modbus register as a signed integer."""
    raw = struct.pack(">H", word)
    return struct.unpack(">h", raw)[0]


def get_bit(word: int, bit: int) -> bool:
    return bool((word >> bit) & 1)


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------

class ModbusBridge:
    def __init__(self, opts: dict):
        self.opts = opts
        self.mqtt_client = mqtt.Client(client_id="gruenbeck_spaliq", protocol=mqtt.MQTTv5)
        self._running = True

    # ------------------------------------------------------------------
    # MQTT
    # ------------------------------------------------------------------

    def _mqtt_connect(self):
        username = self.opts.get("mqtt_username", "")
        password = self.opts.get("mqtt_password", "")
        if username:
            self.mqtt_client.username_pw_set(username, password)
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
        self.mqtt_client.connect(self.opts["mqtt_host"], self.opts["mqtt_port"], keepalive=60)
        self.mqtt_client.loop_start()

    def _on_mqtt_connect(self, client, userdata, flags, rc, props=None):
        if rc == 0:
            log.info("Connected to MQTT broker")
            if self.opts.get("ha_discovery", True):
                self._publish_discovery()
        else:
            log.error("MQTT connection failed, rc=%s", rc)

    def _on_mqtt_disconnect(self, client, userdata, rc, props=None):
        log.warning("Disconnected from MQTT broker (rc=%s)", rc)

    def _sensor_topic(self, name: str) -> str:
        return f"{self.opts['mqtt_topic_prefix']}/sensor/{name}/state"

    def _binary_sensor_topic(self, name: str) -> str:
        return f"{self.opts['mqtt_topic_prefix']}/binary_sensor/{name}/state"

    def _publish_discovery(self):
        disc_prefix = self.opts.get("ha_discovery_prefix", "homeassistant")
        device_info = {
            "identifiers": ["gruenbeck_spaliq"],
            "name": "Grünbeck spaliQ",
            "manufacturer": "Grünbeck",
            "model": "spaliQ Professional",
        }

        count = 0

        # Numeric sensors — operating hours
        for _label, mqtt_name, _reg in DINT_REGISTERS:
            friendly = mqtt_name.replace("_", " ").title()
            config_topic = f"{disc_prefix}/sensor/gruenbeck_{mqtt_name}/config"
            payload = {
                "name": friendly,
                "unique_id": f"gruenbeck_spaliq_{mqtt_name}",
                "state_topic": self._sensor_topic(mqtt_name),
                "unit_of_measurement": "h",
                "device_class": "duration",
                "device": device_info,
            }
            self.mqtt_client.publish(config_topic, json.dumps(payload), retain=True)
            count += 1

        # Numeric sensors — analog measurements
        for label, mqtt_name, _reg, _scale, unit, device_class in INT16_REGISTERS:
            config_topic = f"{disc_prefix}/sensor/gruenbeck_{mqtt_name}/config"
            payload: dict = {
                "name": label,
                "unique_id": f"gruenbeck_spaliq_{mqtt_name}",
                "state_topic": self._sensor_topic(mqtt_name),
                "unit_of_measurement": unit,
                "device": device_info,
            }
            if device_class:
                payload["device_class"] = device_class
            self.mqtt_client.publish(config_topic, json.dumps(payload), retain=True)
            count += 1

        # Binary sensors — status / alarm / fault bits
        for _reg, _bit, mqtt_name, friendly_name, device_class in BIT_REGISTERS:
            config_topic = f"{disc_prefix}/binary_sensor/gruenbeck_{mqtt_name}/config"
            payload = {
                "name": friendly_name,
                "unique_id": f"gruenbeck_spaliq_{mqtt_name}",
                "state_topic": self._binary_sensor_topic(mqtt_name),
                "payload_on": "ON",
                "payload_off": "OFF",
                "device": device_info,
            }
            if device_class:
                payload["device_class"] = device_class
            self.mqtt_client.publish(config_topic, json.dumps(payload), retain=True)
            count += 1

        log.info("MQTT auto-discovery published (%d entities)", count)

    # ------------------------------------------------------------------
    # Modbus
    # ------------------------------------------------------------------

    def _read_all_registers(self) -> list[int] | None:
        """Read registers 0–20 via raw TCP socket.

        The device returns a valid Modbus TCP response but with a non-standard
        Protocol Identifier in the MBAP header and one extra trailing byte,
        both of which cause pymodbus to reject the frame.  We send a standard
        request ourselves and parse the register data directly from bytes 9–50
        of the response (6 MBAP + unit + func + byte-count + 42 data bytes).
        """
        host = self.opts["modbus_host"]
        port = self.opts["modbus_port"]
        unit_id = self.opts.get("modbus_unit_id", 1)
        count = 21

        # Standard Modbus TCP read-holding-registers request (12 bytes):
        #   MBAP: trans_id=1, proto_id=0, length=6
        #   PDU:  unit_id, func=3, start_addr=0, quantity=21
        request = struct.pack(">HHHBBHH", 1, 0, 6, unit_id, 3, 0, count)

        try:
            with socket.create_connection((host, port), timeout=10) as sock:
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
            log.error("Cannot connect to Modbus device at %s:%s — %s", host, port, exc)
            return None

        expected = 9 + count * 2  # 51 bytes
        if len(data) < expected:
            log.error(
                "Short response from device: %d bytes (expected %d)", len(data), expected
            )
            return None

        log.debug("Raw Modbus response (%d bytes): %s", len(data), data.hex())

        func_code = data[7]
        if func_code & 0x80:
            log.error("Modbus exception response from device, error code 0x%02x", data[8])
            return None
        if func_code != 0x03:
            log.error("Unexpected function code: 0x%02x (expected 0x03)", func_code)
            return None

        regs_raw = data[9 : 9 + count * 2]
        return [struct.unpack(">H", regs_raw[i * 2 : i * 2 + 2])[0] for i in range(count)]

    # ------------------------------------------------------------------
    # Poll + publish
    # ------------------------------------------------------------------

    def _poll_and_publish(self):
        regs = self._read_all_registers()
        if regs is None:
            return

        # DInt operating-hour counters (registers 0–7, paired)
        for _label, mqtt_name, start in DINT_REGISTERS:
            value = decode_dint(regs[start], regs[start + 1])
            self.mqtt_client.publish(self._sensor_topic(mqtt_name), str(value))
            log.debug("%s = %s h", mqtt_name, value)

        # Int16 analog measurements (registers 8–15)
        for _label, mqtt_name, reg, scale, unit, _dc in INT16_REGISTERS:
            raw = decode_int16(regs[reg])
            value = raw / scale if scale != 1 else raw
            self.mqtt_client.publish(self._sensor_topic(mqtt_name), str(value))
            log.debug("%s = %s %s", mqtt_name, value, unit)

        # Bit-field status / alarm / fault words (registers 16–20)
        for reg, bit, mqtt_name, _label, _dc in BIT_REGISTERS:
            state = "ON" if get_bit(regs[reg], bit) else "OFF"
            self.mqtt_client.publish(self._binary_sensor_topic(mqtt_name), state)
            log.debug("%s = %s", mqtt_name, state)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        self._mqtt_connect()
        poll_interval = self.opts.get("poll_interval", 30)
        log.info("Polling every %d seconds", poll_interval)
        while self._running:
            try:
                self._poll_and_publish()
            except Exception as exc:  # noqa: BLE001
                log.exception("Unexpected error during poll: %s", exc)
            time.sleep(poll_interval)

    def stop(self):
        self._running = False
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()


def main():
    opts = load_options()
    bridge = ModbusBridge(opts)

    def _shutdown(signum, frame):
        log.info("Received signal %s, shutting down...", signum)
        bridge.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    bridge.run()


if __name__ == "__main__":
    main()
