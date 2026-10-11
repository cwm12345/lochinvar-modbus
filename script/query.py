#!/usr/bin/env python3
# Written by Claude, guided by Chris.

"""Query a Lochinvar boiler with a MODB-I-O board and print every value."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging

from modbus_connection import ModbusError
from modbus_connection.cli_helper import (
    CountingUnit,
    add_connection_args,
    connect_from_args,
    print_component,
)

from lochinvar_modbus import COMPONENTS, LochinvarBoiler, TemperatureUnit

# A gateway answering Modbus TCP, or the board's RS-485 line directly or
# through a serial server (socket://host:port). Both framers are named on
# purpose: offered a single framer, cli_helper defaults every transport to it,
# and a TCP gateway spoken to in RTU framing just times out.
CONNECTIONS = (("tcp", "socket"), ("serial", "rtu"))

EXAMPLES = """examples:
  uv run script/query.py 192.168.1.50 --port 502 --unit 1 --fahrenheit
  uv run script/query.py /dev/ttyUSB0 --transport serial --baudrate 9600 --unit 1 --raw
"""


async def main() -> int:
    """Read one boiler and print it."""
    logging.getLogger().addHandler(logging.NullHandler())

    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_connection_args(parser, connections=CONNECTIONS)
    parser.add_argument("--unit", type=int, default=1, help="Modbus unit id")
    parser.add_argument(
        "--fahrenheit",
        action="store_true",
        help="the boiler's display is set to Fahrenheit (default Celsius)",
    )
    parser.add_argument(
        "--raw", action="store_true", help="also dump every register read, as JSON"
    )
    args = parser.parse_args()
    temperature_unit = (
        TemperatureUnit.FAHRENHEIT if args.fahrenheit else TemperatureUnit.CELSIUS
    )

    try:
        connection = await connect_from_args(args)
    except ModbusError as err:
        print(f"Could not connect to {args.target}: {str(err) or type(err).__name__}")
        return 1

    counting = CountingUnit(connection.for_unit(args.unit))
    boiler = LochinvarBoiler(counting, temperature_unit)
    try:
        report = await boiler.async_update()
        reads = counting.reads
        raw = await boiler.async_read_raw() if args.raw else None
    except ModbusError as err:
        print(f"Could not read the boiler: {str(err) or type(err).__name__}")
        return 1
    finally:
        await connection.close()

    for name in COMPONENTS:
        print()
        print_component(getattr(boiler, name), title=name)

    s, b = boiler.status, boiler.bms
    unit = temperature_unit.value
    print("\nDecoded")
    print(f"  status            {s.status!r}")
    print(f"  blocking          {s.blocking!r}")
    print(f"  lockout           {s.lockout!r}")
    print(f"  inputs on         {s.inputs!r}")
    print(f"  outlet / inlet    {s.outlet_temperature} / {s.inlet_temperature} {unit}")
    print(f"  flue              {s.flue_temperature} {unit}")
    print(f"  outlet setpoint   {s.outlet_setpoint} {unit}")
    print(f"  tank / setpoint   {b.tank_temperature} / {b.tank_setpoint} {unit}")
    print(f"  outdoor           {b.outdoor_temperature} {unit}")
    if report.failed:
        print("\nFailed to read:")
        for name, error in report.failed.items():
            print(f"  {name}: {str(error) or type(error).__name__}")
    if raw is not None:
        print("\nRaw registers")
        print(json.dumps(raw, indent=2))
    print(f"\n{reads} Modbus reads")
    return 0


raise SystemExit(asyncio.run(main()))
