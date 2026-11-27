# Written by Claude, guided by Chris.
"""Turn the boiler's raw temperature words into degrees, in whichever unit it sends."""

from __future__ import annotations

from .enums import TemperatureUnit

# A disconnected sensor reads the control's 500 °C open-circuit value, which a
# Fahrenheit boiler sends as 932 °F. No real boiler reading comes near either.
_OPEN_SENSOR = {TemperatureUnit.CELSIUS: 499.0, TemperatureUnit.FAHRENHEIT: 930.0}

# A setpoint of 0 °C (32 °F) means there is no active setpoint.
_NO_SETPOINT = {TemperatureUnit.CELSIUS: 0.0, TemperatureUnit.FAHRENHEIT: 32.0}


def _fahrenheit_word(celsius_tenths: int) -> int:
    """The word a Fahrenheit board sends for a reading in tenths of a degree C.

    The board converts with 16-bit unsigned arithmetic, so below 0 °C the
    multiply wraps: -0.1 °C arrives as 13425, -1.0 °C as 13409, -40 °C as 12707.
    Seen on a Knight WHB399N's outdoor sensor, 2026-11-19.
    """
    return ((celsius_tenths & 0xFFFF) * 9 & 0xFFFF) // 5 + 320


# Wrapped sub-zero words back to tenths of a degree C, down to the sensors'
# -40 °C floor. They sit well above the 932 °F open-sensor value.
_BELOW_ZERO_F = {_fahrenheit_word(-tenths): -tenths for tenths in range(1, 401)}


def measured(raw: int | None, unit: TemperatureUnit) -> float | None:
    """Decode a measured temperature: tenths of a degree in either unit.

    Returns None for a missing word or a disconnected sensor.
    """
    if raw is None:
        return None
    if unit is TemperatureUnit.FAHRENHEIT and raw in _BELOW_ZERO_F:
        return round(_BELOW_ZERO_F[raw] * 0.18 + 32, 1)
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


# What the board takes for a written sensor value (manual: -40 to 60 C).
_WRITABLE = {
    TemperatureUnit.CELSIUS: (-40.0, 60.0),
    TemperatureUnit.FAHRENHEIT: (32.0, 140.0),
}


def encode_measured(degrees: float, unit: TemperatureUnit) -> int:
    """Encode a temperature to write into a sensor register: tenths of a degree.

    Fahrenheit is limited to 32 F and up. A Fahrenheit board stores a written
    word as ``(((word - 320) & 0xFFFF) * 5 & 0xFFFF) // 9`` tenths of a
    degree C, unsigned, so below 32 F the subtraction wraps and the stored
    value lands at 713-728 C. No word can produce a negative C. Checked live
    on a Knight Wall Hung: a fed 31.9 F (or 30, 20, 5 F) put it into
    warm-weather shutdown, with the same 10 F latch as a fed 75 F. All 14
    readbacks matched this formula. 32.0 F is fine. A reset curve's target
    is at its cap well above freezing, so a caller can clamp to 32 F without
    changing what the boiler does.
    Celsius follows the manual (signed tenths, no conversion) and is
    unchecked; it may well take sub-zero values.

    Raises ``ValueError`` outside the writable range.
    """
    low, high = _WRITABLE[unit]
    if not low <= degrees <= high:
        raise ValueError(f"{degrees} {unit.value} is outside {low} to {high}")
    return round(degrees * 10) & 0xFFFF
