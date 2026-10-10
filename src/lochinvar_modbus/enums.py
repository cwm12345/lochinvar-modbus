# Written by Claude, guided by Chris.
"""Coded values the boiler reports: units, status, blocking and lockout codes, inputs.

The code tables are transcribed from the Lochinvar MODB-I-O Modbus and BACnet
manual (Rev N), troubleshooting section. A code the manual doesn't list is kept
as a plain int by the components, never forced into one of these.
"""

from __future__ import annotations

from enum import IntEnum, IntFlag, StrEnum

__all__ = [
    "BlockingCode",
    "DiscreteInputs",
    "LockoutCode",
    "StatusCode",
    "TemperatureUnit",
]

CODE_NOT_PRESENT = 32767
"""What the status, blocking and lockout registers read when there's no code."""


class TemperatureUnit(StrEnum):
    """The unit the boiler sends temperatures in.

    The manual documents Celsius (measured values in tenths of a degree,
    setpoints in half degrees). A boiler whose display is set to Fahrenheit
    sends Fahrenheit instead: measured values in tenths of a degree and
    setpoints in whole degrees. Nothing on the bus says which, so the caller
    states it.
    """

    CELSIUS = "°C"
    FAHRENHEIT = "°F"


class StatusCode(IntEnum):
    """What the boiler is doing (input register 30014)."""

    BLOCKED_HIGH_OUTLET_TEMPERATURE = 2
    BLOCKED_HIGH_FLUE_TEMPERATURE = 3
    BLOCKED_HIGH_DELTA_T = 4
    BLOCKED_LOW_24VAC = 8
    OUTDOOR_SHUTDOWN = 9
    SWITCHED_OFF = 10
    CASCADE_COMMUNICATION_FAULT = 12
    SERVICE = 16
    HOT_WATER = 19
    """DHW function, storage tank."""
    HEAT_DEMAND_THERMOSTAT = 21
    HEAT_DEMAND_BMS = 22
    HEAT_DEMAND_CASCADE = 23
    FREEZE_PROTECTION = 30
    HOT_WATER_PUMP_DELAY = 32
    HEATING_PUMP_DELAY = 33
    """Space heat demand ended; the pump is running out its delay."""
    IDLE = 34
    """No heat function, after the pump delay."""
    LOCKOUT = 40
    UPDATING = 32764
    HOT_WATER_BLOCKED_NO_TANK_SENSOR = 32765
    BURNER_SHUT_DOWN_MANUALLY = 32766


class BlockingCode(IntEnum):
    """Why a heat demand is being held back (input register 30015)."""

    NONE = 0
    HEATING_BLOCKED = 1
    LOW_24VAC = 2
    GENERAL = 3
    MANUAL_RESET_HIGH_LIMIT_OPEN = 4
    SWITCHED_OFF = 5
    CASCADE_COMMUNICATION = 6
    HIGH_DELTA_T = 7
    HIGH_FLUE_TEMPERATURE = 8
    HIGH_OUTLET_TEMPERATURE = 9
    SERVICE = 10
    HOT_WATER_HIGH_OUTLET_TEMPERATURE = 12
    ANTI_CYCLING = 13
    HOT_WATER_FAN_PROBLEM = 14
    NO_SYSTEM_SENSOR = 15
    FAN_LIMITED_HIGH_OUTLET_TEMPERATURE = 16
    FAN_MINIMUM_RAISED_LOW_FLAME_CURRENT = 17
    FAN_LIMITED_HIGH_DELTA_T = 18
    FAN_LIMITED_HIGH_FLUE_TEMPERATURE = 19


class LockoutCode(IntEnum):
    """Why the boiler locked out (input register 30016).

    The register changes constantly during normal operation; it only means a
    lockout while the status code is ``StatusCode.LOCKOUT``.
    """

    PARAMETERS_NOT_PROGRAMMED = 161
    NO_RESET_ALLOWED = 164
    AUTO_RESET_HIGH_LIMIT = 166
    BLOCKED_DRAIN = 167
    LOUVER_PROVING = 168
    GAS_PRESSURE_SWITCH = 169
    FLOW_SWITCH = 170
    FLUE_SENSOR_SHORT = 177
    FLUE_SENSOR_OPEN = 178
    INLET_SENSOR_SHORT = 179
    INLET_SENSOR_OPEN = 180
    OUTLET_SENSOR_SHORT = 192
    OUTLET_SENSOR_OPEN = 193
    EEPROM_CRC_FAILED = 204
    EEPROM_PROGRAMMED = 205
    EEPROM_PROGRAMMING_ERROR = 206
    EEPROM_WRITE_ERROR = 207
    WATCHDOG = 229
    FAN_LOW = 230
    """Fan speed low when it should be high."""
    FAN_HIGH = 231
    """Fan speed high when it should be low."""
    NO_FLAME_WHILE_RUNNING = 232
    NO_FLAME_AFTER_IGNITION = 233
    AIR_PRESSURE_SWITCH_AND_FAN = 234
    AIR_PRESSURE_SWITCH_NOT_CLOSED = 235
    AIR_PRESSURE_SWITCH_NOT_OPEN = 236
    FLAME_OUT_OF_SEQUENCE = 237
    GAS_VALVE_RELAY_TEST_FAILED = 239
    MANUAL_RESET_HIGH_LIMIT = 240


class DiscreteInputs(IntFlag):
    """The boiler's discrete inputs, as packed into input registers 30001-30003.

    Bit n is discrete input 10001 + n: register 30001 holds inputs 1-16,
    30002 inputs 17-32 and 30003 inputs 33-48, least significant bit first.
    The manual gives each one only as 1=ON / 0=OFF; for the safety switches it
    does not say whether ON means made (normal) or tripped.
    """

    FLOW_SWITCH = 1 << 1
    GAS_PRESSURE_SWITCH = 1 << 2
    LOUVER_PROVING_SWITCH = 1 << 3
    AIR_PRESSURE_SWITCH = 1 << 4
    BLOCKED_DRAIN_SWITCH = 1 << 5
    AUTO_RESET_HIGH_LIMIT = 1 << 6
    FLAME = 1 << 7
    ROOM_THERMOSTAT_1 = 1 << 8
    TANK_THERMOSTAT = 1 << 9
    ROOM_THERMOSTAT_2 = 1 << 23
    RUN_TIME_CONTACTS = 1 << 32
    ALARM_CONTACTS = 1 << 33
    CH_PUMP = 1 << 34
    """The boiler (central heating) pump."""
    DHW_PUMP = 1 << 35
    LOUVER_RELAY = 1 << 36
    GAS_VALVE = 1 << 37
    SYSTEM_PUMP = 1 << 38
    DHW_RECIRCULATION_PUMP = 1 << 43
