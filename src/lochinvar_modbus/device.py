# Written by Claude, guided by Chris.
"""The top-level object for a Lochinvar boiler with a Modbus communication board."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from modbus_connection.model import Device, Raw, UpdateReport

from .bms import Bms
from .enums import TemperatureUnit
from .status import Status

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

__all__ = ["COMPONENTS", "LochinvarBoiler"]

COMPONENTS: tuple[str, ...] = ("status", "bms")
"""Both register tables; each is one block read."""


class LochinvarBoiler(Device):
    """A Lochinvar boiler or water heater with the MODB-I-O communication board.

    Covers the models the board's manual lists: Knight, Knight XL, Armor,
    Outdoor Knight/Armor, AQUAS, FTXL, Wall Mount, Wall Hung, Wall Mount Armor
    and Shield. Hand it a ``ModbusUnit``; it owns no connection. The board
    speaks Modbus RTU (9600 or 19200 baud, set by DIP switch), usually reached
    through a gateway.

    ``temperature_unit`` must match what the boiler sends, which follows its
    display setting; see ``TemperatureUnit``.
    """

    def __init__(self, unit: ModbusUnit, temperature_unit: TemperatureUnit) -> None:
        super().__init__(unit)
        self.temperature_unit = temperature_unit
        self.status = Status(unit, temperature_unit)
        self.bms = Bms(unit, temperature_unit)

    async def async_update(self) -> UpdateReport:
        """Refresh both register tables in one report."""
        return await self.async_poll(COMPONENTS)

    async def async_read_raw(self, names: Iterable[str] | None = None) -> Raw:
        """Every register this boiler reads, undecoded, for diagnostics."""
        return await super().async_read_raw(COMPONENTS if names is None else names)
