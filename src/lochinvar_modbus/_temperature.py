# Written by Claude, guided by Chris.
"""Turn the boiler's raw temperature words into degrees, in whichever unit it sends."""

from __future__ import annotations

from .enums import TemperatureUnit

# A disconnected sensor reads the control's 500 °C open-circuit value, which a
# Fahrenheit boiler sends as 932 °F. No real boiler reading comes near either.
_OPEN_SENSOR = {TemperatureUnit.CELSIUS: 499.0, TemperatureUnit.FAHRENHEIT: 930.0}

# A setpoint of 0 °C (32 °F) means there is no active setpoint.
_NO_SETPOINT = {TemperatureUnit.CELSIUS: 0.0, TemperatureUnit.FAHRENHEIT: 32.0}


def measured(raw: int | None, unit: TemperatureUnit) -> float | None:
    """Decode a measured temperature: tenths of a degree in either unit.

    Returns None for a missing word or a disconnected sensor.
    """
    if raw is None:
        return None
    value = raw / 10
    return None if value >= _OPEN_SENSOR[unit] else value


def setpoint(raw: int | None, unit: TemperatureUnit) -> float | None:
    """Decode a setpoint: whole degrees in Fahrenheit, half degrees in Celsius.

    Returns None for a missing word or when there is no active setpoint.
    """
    if raw is None:
        return None
    value = float(raw) if unit is TemperatureUnit.FAHRENHEIT else raw * 0.5
    return None if value <= _NO_SETPOINT[unit] else value
