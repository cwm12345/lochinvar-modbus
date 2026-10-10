# Written by Claude, guided by Chris.
"""The MODB-I-O register map, decoded over the mock backend."""

from __future__ import annotations

import pytest
from modbus_connection import ModbusTimeoutError
from modbus_connection.mock import MockModbusUnit

from lochinvar_modbus import (
    COMPONENTS,
    BlockingCode,
    DiscreteInputs,
    LochinvarBoiler,
    LockoutCode,
    StatusCode,
    TemperatureUnit,
)


def test_nothing_before_the_first_read(boiler: LochinvarBoiler) -> None:
    assert boiler.status.outlet_temperature is None
    assert boiler.status.inputs is None
    assert boiler.status.status is None
    assert boiler.bms.tank_setpoint is None


async def test_live_fahrenheit_boiler(boiler: LochinvarBoiler) -> None:
    report = await boiler.async_update()
    assert report.updated == set(COMPONENTS)
    assert report.complete

    s = boiler.status
    assert s.outlet_temperature == 98.6
    assert s.inlet_temperature == 97.1
    assert s.flue_temperature == 84.3
    assert s.outlet_setpoint is None  # 32 F: no demand
    assert s.system_setpoint is None
    assert s.firing_rate == 0
    assert s.boiler_pump_speed == 9
    assert s.system_pump_speed == 0
    assert s.cascade_total_power == 0
    assert s.status is StatusCode.HEATING_PUMP_DELAY
    assert s.status_code == 33
    assert s.blocking is BlockingCode.NONE
    assert s.lockout_code is None  # 32767, code not present
    assert s.locked_out is False
    assert s.lockout is None

    b = boiler.bms
    assert b.tank_setpoint == 124.0
    assert b.tank_temperature == 119.6
    assert b.outdoor_temperature == 62.9
    assert b.system_supply_temperature is None  # open circuit
    assert b.dhw_recirculation_temperature is None
    assert (b.configuration, b.command, b.rate_command) == (0, 0, 0)


async def test_discrete_inputs_unpack(boiler: LochinvarBoiler) -> None:
    await boiler.async_update()
    inputs = boiler.status.inputs
    assert inputs == (
        DiscreteInputs.FLOW_SWITCH
        | DiscreteInputs.GAS_PRESSURE_SWITCH
        | DiscreteInputs.LOUVER_PROVING_SWITCH
        | DiscreteInputs.AIR_PRESSURE_SWITCH
        | DiscreteInputs.BLOCKED_DRAIN_SWITCH
        | DiscreteInputs.CH_PUMP
    )
    assert boiler.status.input_on(DiscreteInputs.CH_PUMP) is True
    assert boiler.status.input_on(DiscreteInputs.FLAME) is False


async def test_inputs_in_the_upper_words(
    unit: MockModbusUnit, boiler: LochinvarBoiler
) -> None:
    unit.input[1] = 1 << 7  # input 24: room thermostat 2
    unit.input[2] = 1 << 11 | 1 << 5  # inputs 44 (DHW recirc pump) and 38 (gas valve)
    await boiler.async_update()
    s = boiler.status
    assert s.input_on(DiscreteInputs.ROOM_THERMOSTAT_2) is True
    assert s.input_on(DiscreteInputs.DHW_RECIRCULATION_PUMP) is True
    assert s.input_on(DiscreteInputs.GAS_VALVE) is True
    assert s.input_on(DiscreteInputs.CH_PUMP) is False


async def test_firing_for_hot_water(
    unit: MockModbusUnit, boiler: LochinvarBoiler
) -> None:
    unit.input[7] = 170  # outlet setpoint 170 F
    unit.input[11] = 57  # firing 57 %
    unit.input[12] = 100  # pump 100 %
    unit.input[13] = 19  # hot water
    await boiler.async_update()
    s = boiler.status
    assert s.outlet_setpoint == 170.0
    assert s.firing_rate == 57
    assert s.boiler_pump_speed == 100
    assert s.status is StatusCode.HOT_WATER


async def test_celsius_boiler_follows_the_manual(unit: MockModbusUnit) -> None:
    # The manual's own worked example: an outlet of 155 F is sent as 683 (68.3 C).
    unit.input[8] = 683
    unit.input[7] = 120  # setpoint in half degrees: 60.0 C
    unit.holding[3] = 120  # tank setpoint 60.0 C
    unit.holding[5] = 0xFF9C  # outdoor -10.0 C
    unit.holding[6] = 5000  # open circuit, 500.0 C
    boiler = LochinvarBoiler(unit, TemperatureUnit.CELSIUS)
    await boiler.async_update()
    assert boiler.status.outlet_temperature == 68.3
    assert boiler.status.outlet_setpoint == 60.0
    assert boiler.bms.tank_setpoint == 60.0
    assert boiler.bms.outdoor_temperature == -10.0
    assert boiler.bms.system_supply_temperature is None


async def test_celsius_zero_setpoint_means_none(unit: MockModbusUnit) -> None:
    unit.input[7] = 0
    boiler = LochinvarBoiler(unit, TemperatureUnit.CELSIUS)
    await boiler.async_update()
    assert boiler.status.outlet_setpoint is None


async def test_lockout_reason_only_while_locked_out(
    unit: MockModbusUnit, boiler: LochinvarBoiler
) -> None:
    unit.input[15] = 233  # changes constantly; not a lockout by itself
    await boiler.async_update()
    assert boiler.status.lockout is None
    assert boiler.status.lockout_code == 233

    unit.input[13] = 40
    await boiler.async_update()
    assert boiler.status.locked_out is True
    assert boiler.status.lockout is LockoutCode.NO_FLAME_AFTER_IGNITION


async def test_unlisted_codes_stay_ints(
    unit: MockModbusUnit, boiler: LochinvarBoiler
) -> None:
    unit.input[13] = 77
    unit.input[14] = 11
    await boiler.async_update()
    assert boiler.status.status == 77
    assert not isinstance(boiler.status.status, StatusCode)
    assert boiler.status.blocking == 11


async def test_a_full_poll_is_two_reads(
    unit: MockModbusUnit, boiler: LochinvarBoiler
) -> None:
    await boiler.async_update()
    blocks = sorted(
        (event.register_type, event.address, event.count) for event in unit.read_events
    )
    assert blocks == [("holding", 0, 8), ("input", 0, 16)]


async def test_a_silent_boiler_raises(
    unit: MockModbusUnit, boiler: LochinvarBoiler
) -> None:
    unit.fail_requests(ModbusTimeoutError())
    with pytest.raises(ModbusTimeoutError):
        await boiler.async_update()


async def test_raw_dump_covers_both_tables(boiler: LochinvarBoiler) -> None:
    raw = await boiler.async_read_raw()
    assert raw["input"][13] == 33
    assert raw["holding"][3] == 124
