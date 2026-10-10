# Written by Claude, guided by Chris.
"""The input register table: inputs, temperatures, firing, pumps and codes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from modbus_connection.model import Component, integer

from . import _temperature
from .enums import (
    CODE_NOT_PRESENT,
    BlockingCode,
    DiscreteInputs,
    LockoutCode,
    StatusCode,
    TemperatureUnit,
)

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit

__all__ = ["Status"]


def _code[E: (StatusCode, BlockingCode, LockoutCode)](
    raw: int | None, table: type[E]
) -> E | int | None:
    """Look a code up in its table, keeping an unlisted code as a plain int."""
    if raw is None:
        return None
    try:
        return table(raw)
    except ValueError:
        return raw


class Status(Component):
    """Input registers 30001-30016, read in one block.

    Everything the boiler reports about itself: its discrete inputs (packed
    into three words), setpoints, temperatures, firing rate, pump speeds and
    the status, blocking and lockout codes.
    """

    register_space = "input"

    inputs_1_16 = integer(0, signed=False)
    """30001, discrete inputs 1-16."""
    inputs_17_32 = integer(1, signed=False)
    """30002, discrete inputs 17-32."""
    inputs_33_48 = integer(2, signed=False)
    """30003, discrete inputs 33-48."""

    system_setpoint_raw = integer(3, signed=False)
    """30004, system/cascade setpoint, undecoded. See ``system_setpoint``."""

    system_pump_speed = integer(4, signed=False, unit="%")
    """30005."""

    cascade_total_power = integer(5, signed=False, unit="%")
    """30006, the cascade's total capacity. 0 on a boiler not in a cascade."""

    cascade_current_power = integer(6, signed=False, unit="%")
    """30007."""

    outlet_setpoint_raw = integer(7, signed=False)
    """30008, outlet setpoint, undecoded. See ``outlet_setpoint``."""

    outlet_temperature_raw = integer(8)
    """30009, undecoded. See ``outlet_temperature``."""
    inlet_temperature_raw = integer(9)
    """30010, undecoded."""
    flue_temperature_raw = integer(10)
    """30011, undecoded."""

    firing_rate = integer(11, signed=False, unit="%")
    """30012."""

    boiler_pump_speed = integer(12, signed=False, unit="%")
    """30013."""

    status_code = integer(13, signed=False, nan=CODE_NOT_PRESENT)
    """30014, raw. See ``status``."""
    blocking_code = integer(14, signed=False, nan=CODE_NOT_PRESENT)
    """30015, raw. See ``blocking``."""
    lockout_code = integer(15, signed=False, nan=CODE_NOT_PRESENT)
    """30016, raw. Changes constantly in normal operation; see ``lockout``."""

    def __init__(self, unit: ModbusUnit, temperature_unit: TemperatureUnit) -> None:
        super().__init__(unit)
        self.temperature_unit = temperature_unit

    @property
    def inputs(self) -> DiscreteInputs | None:
        """The discrete inputs that are on."""
        low, mid, high = self.inputs_1_16, self.inputs_17_32, self.inputs_33_48
        if low is None or mid is None or high is None:
            return None
        return DiscreteInputs(low | mid << 16 | high << 32)

    def input_on(self, which: DiscreteInputs) -> bool | None:
        """Whether one discrete input is on."""
        inputs = self.inputs
        return None if inputs is None else which in inputs

    @property
    def system_setpoint(self) -> float | None:
        """The system/cascade setpoint, or None when there is none."""
        return _temperature.setpoint(self.system_setpoint_raw, self.temperature_unit)

    @property
    def outlet_setpoint(self) -> float | None:
        """The outlet water target, or None when there is no demand."""
        return _temperature.setpoint(self.outlet_setpoint_raw, self.temperature_unit)

    @property
    def outlet_temperature(self) -> float | None:
        """Water leaving the boiler."""
        return _temperature.measured(self.outlet_temperature_raw, self.temperature_unit)

    @property
    def inlet_temperature(self) -> float | None:
        """Water entering the boiler."""
        return _temperature.measured(self.inlet_temperature_raw, self.temperature_unit)

    @property
    def flue_temperature(self) -> float | None:
        """Flue gas leaving the boiler."""
        return _temperature.measured(self.flue_temperature_raw, self.temperature_unit)

    @property
    def status(self) -> StatusCode | int | None:
        """What the boiler is doing; an unlisted code stays an int."""
        return _code(self.status_code, StatusCode)

    @property
    def blocking(self) -> BlockingCode | int | None:
        """Why a demand is held back; an unlisted code stays an int."""
        return _code(self.blocking_code, BlockingCode)

    @property
    def locked_out(self) -> bool | None:
        """Whether the boiler is in lockout."""
        status = self.status_code
        return None if status is None else status == StatusCode.LOCKOUT

    @property
    def lockout(self) -> LockoutCode | int | None:
        """The lockout reason, only while the boiler is locked out."""
        if not self.locked_out:
            return None
        return _code(self.lockout_code, LockoutCode)
