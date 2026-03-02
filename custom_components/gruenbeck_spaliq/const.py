"""Constants and register definitions for Grünbeck spaliQ."""
import struct

DOMAIN = "gruenbeck_spaliq"

# ---------------------------------------------------------------------------
# Register layout (from BA_100142280000_de_084_spaliQ Professional)
# ---------------------------------------------------------------------------

# 32-bit operating-hour counters (DInt, high word first).
# Each entry: (friendly_name, key, start_register)
DINT_REGISTERS = [
    ("Betriebsstunden Mess- und Regelanlage",        "operating_hours_system",      0),
    ("Betriebsstunden pH-Dosierung 1",               "operating_hours_ph_dosing_1", 2),
    ("Betriebsstunden Desinfektionsdosierung",        "operating_hours_disinfection", 4),
    ("Betriebsstunden Flockungsdosierung/pH-Dos. 2", "operating_hours_flocculation", 6),
]

# 16-bit analog measurements.
# Each entry: (friendly_name, key, register, scale, unit, ha_device_class)
# Decoded as: actual = decode_int16(raw) / scale
INT16_REGISTERS = [
    ("pH-Wert Beckenwasser",       "ph_value",          8,  100, "pH",   None),
    ("Desinfektionswert",          "disinfection_value", 9,  100, "mg/L", None),
    ("Redox-Wert",                 "redox_value",        10,   1, "mV",   None),
    ("Wassertemperatur",           "water_temperature",  11,  10, "°C",   "temperature"),
    ("Raumtemperatur/Luftfeuchte", "room_sensor_1",      14,  10, "°C",   "temperature"),
    ("Raumtemperatur/Luftfeuchte", "room_sensor_2",      15,  10, "°C",   "temperature"),
]

# Bit-field status/alarm/fault words.
# Each entry: (register, bit, key, friendly_name, ha_device_class)
BIT_REGISTERS = [
    # Register 16 – Betriebsmeldung / Anlagenstatus
    (16,  0, "status_pulse",              "Status Puls",                    None),
    (16,  1, "heartbeat",                 "Lebensbit (Anlagenstatus)",       None),

    # Register 17 – Info-meldung Teil 1
    (17,  0, "mode_normal_bathing",       "Normalbaden aktiv",               None),
    (17,  2, "mode_superchlorination",    "Hochchlorung aktiv",              None),
    (17,  3, "mode_economy",              "Sparbetrieb aktiv",               None),
    (17,  4, "mode_part_load",            "Teillastbetrieb aktiv",           None),
    (17,  5, "req_superchlorination",     "Hochchlorung angefordert",        None),
    (17,  6, "req_economy",               "Sparbetrieb angefordert",         None),
    (17,  7, "req_part_load",             "Teillastbetrieb angefordert",     None),
    (17,  8, "dosing_ph_1",              "pH-Dosierung 1 in Betrieb",       None),
    (17,  9, "dosing_disinfection",       "Desinfektionsdosierung",          None),
    (17, 10, "dosing_flocculation",       "Flockungsdosierung/pH-Dos. 2",    None),
    (17, 11, "heating",                   "Heizung",                         None),
    (17, 14, "collective_message_1",      "Sammelmeldung 1",                 "problem"),
    (17, 15, "collective_message_2",      "Sammelmeldung 2",                 "problem"),

    # Register 18 – Info-meldung Teil 2
    (18,  0, "info_maintenance",          "Wartung fällig",                  "problem"),
    (18,  1, "alarm_ph_low",              "pH-Wert zu niedrig",              "problem"),
    (18,  2, "alarm_ph_high",             "pH-Wert zu hoch",                 "problem"),
    (18,  3, "alarm_disinfection_low",    "Desinfektion zu niedrig",         "problem"),
    (18,  4, "alarm_disinfection_high",   "Desinfektion zu hoch",            "problem"),
    (18,  5, "alarm_redox_low",           "Redox-Wert zu niedrig",           "problem"),
    (18,  6, "alarm_redox_high",          "Redox-Wert zu hoch",              "problem"),
    (18, 10, "alarm_no_flow_measurement", "Kein Durchfluss Messwasser",      "problem"),
    (18, 11, "alarm_no_flow_filtrate",    "Kein Durchfluss Filtrat",         "problem"),
    (18, 12, "alarm_refill_ph_1",         "Dosierbehälter pH-Dos. 1 leer",  "problem"),
    (18, 13, "alarm_refill_disinfection", "Dosierbehälter Desinf. leer",    "problem"),
    (18, 14, "alarm_refill_flocculation", "Dosierbehälter Flockung leer",   "problem"),

    # Register 19 – Störmeldung Teil 1
    (19,  0, "fault_collective",          "Sammelstörung",                   "problem"),
    (19,  1, "fault_ph_dosing_1",         "Störung pH-Dosierung 1",          "problem"),
    (19,  2, "fault_disinfection",        "Störung Desinfektionsdosierung",  "problem"),
    (19,  3, "fault_flocculation",        "Störung Flockungsdosierung",      "problem"),
    (19,  4, "fault_container_ph_1",      "Störung Behälter pH-Dos. 1",     "problem"),
    (19,  5, "fault_container_disinfect", "Störung Behälter Desinfektion",   "problem"),
    (19,  6, "fault_container_flocc",     "Störung Behälter Flockung",       "problem"),
    (19,  7, "fault_temperature_sensor",  "Störung Temperatursensor",        "problem"),
]


# ---------------------------------------------------------------------------
# Decode helpers
# ---------------------------------------------------------------------------

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
