<!-- Written by Claude, guided by Chris. -->

# lochinvar-modbus

Read Lochinvar boilers and water heaters fitted with the MODB-I-O Modbus
communication board, as typed Python objects, on top of
[modbus-connection](https://github.com/home-assistant-libs/modbus-connection).

## Supported devices

The models the board's manual (MODB-I-O Rev N) lists: Knight 81-286, Knight XL
400-801, Armor 151-801, Outdoor Knight / Knight XL / Armor, AQUAS 400-801,
FTXL 400-850, Wall Mount 51-211, Wall Hung 55-399, Wall Mount Armor 125-200 and
Shield 125-500. It has been run against one Knight Wall Hung (WHB399N) behind a
Modbus TCP gateway. The board speaks Modbus RTU at 9600 or 19200 baud (DIP
switch 9), no or even parity (DIP switch 10), address set by DIP switches 1-8.

## Temperature units: read this

The manual documents every temperature in Celsius: measured values in tenths
of a degree, setpoints in half degrees. **A boiler whose display is set to
Fahrenheit sends Fahrenheit instead**: measured values in tenths of a degree
and setpoints in whole degrees. Nothing on the bus says which, so you pass it:

```python
from lochinvar_modbus import LochinvarBoiler, TemperatureUnit

boiler = LochinvarBoiler(unit, TemperatureUnit.FAHRENHEIT)
```

How this was established on a live Fahrenheit boiler: a disconnected sensor
reads 9321 (the control's 500 °C open-circuit value, sent as 932.1 °F); its
outdoor sensor read 629 on a 63 °F afternoon; and over 60 days its hot-water
calls started at about 119 °F and stopped at 125-127 °F against a tank
setpoint register of 124, which fits 124 °F, not the 62 °C the manual's scale
would give.

## What it covers

| Component | Table | Registers | What |
| :--- | :--- | :--- | :--- |
| `status` | input | 30001-30016 | Discrete inputs (packed), system and outlet setpoints, outlet/inlet/flue temperatures, firing rate, pump speeds, cascade power, status/blocking/lockout codes |
| `bms` | holding | 40001-40008 | BMS configuration and command words, rate command, tank setpoint, tank/outdoor/system-supply/DHW-recirculation temperatures |

Both tables are read in one block each, two requests per update. The board
rejects any read that touches an address it doesn't map, which is why the
discrete inputs are read from their packed copies in 30001-30003 rather than
the gappy 1xxxx table.

Decoding conventions:

- A disconnected sensor (the 500 °C open-circuit value) reads `None`.
- A setpoint of 0 °C / 32 °F means "no active setpoint" and reads `None`.
- Status, blocking and lockout codes decode to `StatusCode`, `BlockingCode`
  and `LockoutCode`; a code the manual doesn't list stays a plain `int`, and
  32767 ("code not present") reads `None`.
- `status.lockout` only reports a reason while the status code is 40
  (lockout); the manual warns the lockout register changes constantly
  otherwise.

## Writes: the outdoor temperature only

The one write is the outdoor temperature, for a boiler whose own outdoor
sensor reads wrong (in sun, say):

```python
await boiler.bms.async_feed_outdoor_temperature(41.5)  # every few seconds
...
await boiler.bms.async_release_outdoor_temperature()   # back to its sensor
```

This writes 40006 and sets bit 5 of 40001 (`BmsConfiguration.OUTDOOR_TEMPERATURE`).
It only takes effect when ModBus/BACnet is ACTIVE in the boiler's installer
menu (Control Modes). The boiler drops the fed value and goes back to its own
sensor unless the write is repeated within its ModBus timeout (5-120 s,
default 10), so a stopped caller fails safe. While a value is fed,
`bms.outdoor_temperature` reads back that value; the board has no other
register for the sensor. `bms.outdoor_temperature_fed` says which you're
seeing.

Checked live on a Knight Wall Hung in Fahrenheit: feeding 60.0 F moved its
reset target from 109 F to 94 F, as its curve predicts. Fahrenheit writes below
32 F raise `ValueError`, because the encoding for those hasn't been checked
(sub-zero Celsius readings arrive wrapped). Clamp to 32 F instead; a reset
curve is normally at its cap long before then. The other BMS writes (enable,
setpoints, rate) aren't implemented.

## Installation

```
pip install lochinvar-modbus
```

For Home Assistant, you don't need this directly: use the
[ha-lochinvar](https://github.com/cwm12345/ha-lochinvar) integration, which
includes a copy.

## Usage

```python
import asyncio

from modbus_connection import ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection
from lochinvar_modbus import LochinvarBoiler, TemperatureUnit


async def main() -> None:
    connection = ModbusConnection(ModbusTcpParams(host="192.168.1.50", port=502))
    try:
        boiler = LochinvarBoiler(connection.for_unit(1), TemperatureUnit.FAHRENHEIT)
        await boiler.async_update()
        print(boiler.status.status, boiler.status.outlet_temperature)
        print("Tank:", boiler.bms.tank_temperature, "/", boiler.bms.tank_setpoint)
    finally:
        await connection.close()


asyncio.run(main())
```

## Development

```
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

The tests run against modbus-connection's in-memory mock backend, seeded with
registers captured from a live boiler. No hardware is needed.

## License

[Unlicense](LICENSE): public domain.
