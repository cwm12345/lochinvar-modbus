# Written by Claude, guided by Chris.
"""Fixtures: a Lochinvar boiler on modbus-connection's in-memory mock backend."""

from __future__ import annotations

import pytest
from modbus_connection.mock import MockModbusUnit

from lochinvar_modbus import LochinvarBoiler, TemperatureUnit

# A real Knight Wall Hung boiler with its display in Fahrenheit, read live
# while idle with its boiler pump running out a pump delay. Zero-based
# addresses: input register 30001 is input[0], holding register 40001 is
# holding[0].
INPUT: dict[int, int] = {
    0: 62,  # inputs 1-16: flow, gas pressure, louver proving, APS, drain
    1: 0,  # inputs 17-32
    2: 4,  # inputs 33-48: CH pump
    3: 32,  # system setpoint: 32 F, none
    4: 0,  # system pump speed
    5: 0,  # cascade total power
    6: 0,  # cascade current power
    7: 32,  # outlet setpoint: 32 F, none
    8: 986,  # outlet 98.6 F
    9: 971,  # inlet 97.1 F
    10: 843,  # flue 84.3 F
    11: 0,  # firing rate
    12: 9,  # boiler pump speed 9 %
    13: 33,  # status: heating pump delay
    14: 0,  # blocking: none
    15: 32767,  # lockout: code not present
}
HOLDING: dict[int, int] = {
    0: 0,  # configuration
    1: 0,  # command
    2: 0,  # rate command
    3: 124,  # tank setpoint 124 F
    4: 1196,  # tank 119.6 F
    5: 629,  # outdoor 62.9 F
    6: 9321,  # system supply: no sensor (500 C open circuit, sent as 932.1 F)
    7: 9321,  # DHW recirculation: no sensor
}


@pytest.fixture
def unit(mock_modbus_unit: MockModbusUnit) -> MockModbusUnit:
    """The mock unit seeded with the live boiler."""
    for address, value in INPUT.items():
        mock_modbus_unit.input[address] = value
    for address, value in HOLDING.items():
        mock_modbus_unit.holding[address] = value
    return mock_modbus_unit


@pytest.fixture
def boiler(unit: MockModbusUnit) -> LochinvarBoiler:
    """A Fahrenheit boiler reading the seeded unit."""
    return LochinvarBoiler(unit, TemperatureUnit.FAHRENHEIT)
