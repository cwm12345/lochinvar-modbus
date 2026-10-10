# Written by Claude, guided by Chris.
"""The holding register table: the building-management (BMS) exchange registers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from modbus_connection.model import Component, integer

from . import _temperature
from .enums import TemperatureUnit

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

__all__ = ["Bms"]


class Bms(Component):
    """Holding registers 40001-40008, read in one block. Read-only here.

    A BMS controls the boiler by setting configuration bits in 40001 and then
    writing commands, setpoints and sensor values into 40002-40008, which the
    boiler only honors once BMS control is made active in its installer menu
    and the writes are refreshed every few minutes. When nothing is
    controlling it, the boiler reports its own values here: its tank setpoint
    and its tank, outdoor, system supply and DHW recirculation sensors. 40002
    then mirrors its hardwired thermostat demand.
    """

    configuration = integer(0, signed=False)
    """40001, which values the boiler takes from the BMS instead of its own
    inputs (bit 0 enable, 1 tank thermostat, 2 rate command, 3 tank setpoint,
    4 system supply, 5 outdoor, 6 tank, 7 system return temperature)."""

    command = integer(1, signed=False)
    """40002, the BMS enable and thermostat command bits."""

    rate_command = integer(2, signed=False, unit="%")
    """40003, the 0-10 V input / BMS rate or setpoint command."""

    tank_setpoint_raw = integer(3, signed=False)
    """40004, undecoded. See ``tank_setpoint``."""
    tank_temperature_raw = integer(4)
    """40005, undecoded."""
    outdoor_temperature_raw = integer(5)
    """40006, undecoded."""
    system_supply_temperature_raw = integer(6)
    """40007, undecoded."""
    dhw_recirculation_temperature_raw = integer(7)
    """40008, undecoded."""

    def __init__(self, unit: ModbusUnit, temperature_unit: TemperatureUnit) -> None:
        super().__init__(unit)
        self.temperature_unit = temperature_unit

    @property
    def tank_setpoint(self) -> float | None:
        """The hot water tank setpoint."""
        return _temperature.setpoint(self.tank_setpoint_raw, self.temperature_unit)

    @property
    def tank_temperature(self) -> float | None:
        """The hot water tank sensor, or None when none is connected."""
        return _temperature.measured(self.tank_temperature_raw, self.temperature_unit)

    @property
    def outdoor_temperature(self) -> float | None:
        """The outdoor sensor, or None when none is connected."""
        return _temperature.measured(
            self.outdoor_temperature_raw, self.temperature_unit
        )

    @property
    def system_supply_temperature(self) -> float | None:
        """The system supply sensor, or None when none is connected."""
        return _temperature.measured(
            self.system_supply_temperature_raw, self.temperature_unit
        )

    @property
    def dhw_recirculation_temperature(self) -> float | None:
        """The DHW recirculation sensor, or None when none is connected."""
        return _temperature.measured(
            self.dhw_recirculation_temperature_raw, self.temperature_unit
        )
