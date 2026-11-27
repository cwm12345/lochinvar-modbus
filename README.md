<!-- Written by Claude, guided by Chris. -->

# lochinvar-modbus

Read Lochinvar boilers and water heaters fitted with the MODB-I-O Modbus
communication board, as typed Python objects, on top of
[modbus-connection](https://github.com/home-assistant-libs/modbus-connection).

## No MODB-I-O board?

Most of these boilers also have a square **PC Connection** USB port on the
SMART SYSTEM display. [KB1RMA/lochinvar-native-modbus](https://github.com/KB1RMA/lochinvar-native-modbus)
reads that port instead, with no add-on board: ESPHome on an ESP32-S3, or a
Docker container over MQTT. It reads the display's own register set, which is
different from and much larger than the MODB-I-O board's, so the two projects
don't share register numbers. It is read-only too.

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
await boiler.bms.async_feed_outdoor_temperature(41.5)  # at least every 4 min
...
await boiler.bms.async_release_outdoor_temperature()  # back to its sensor
```

This writes 40006 and sets bit 5 of 40001 (`BmsConfiguration.OUTDOOR_TEMPERATURE`).
It only takes effect when ModBus/BACnet is ACTIVE in the boiler's installer
menu (Control Modes). Repeat the write at least every 4 minutes. With no
refresh, the boiler keeps the last fed value for about 5 minutes (measured:
5 min 10 s), then goes back to its own sensor. Its 10 s ModBus timeout
doesn't apply to the outdoor value. So a stopped caller fails safe, but
slowly. While a value is fed,
`bms.outdoor_temperature` reads back that value; the board has no other
register for the sensor. `bms.outdoor_temperature_fed` says which you're
seeing.

Checked live on a Knight Wall Hung in Fahrenheit: feeding 60.0 F moved its
reset target from 109 F to 94 F, as its curve predicts (also 57 F → 102,
64 F → 84). **Never feed below freezing.** On the same boiler, a fed value
under 0 C (31.9 F and colder) is read as hot: the boiler goes into
warm-weather shutdown within seconds. It shows the same signature as a fed
75 F (no outlet setpoint, status heating pump delay, thermostat still
calling), and the same 10 F latch, so a fed 65 F right after keeps heat off.
Why: a Fahrenheit board converts a written word to tenths of a degree C with
the same 16-bit unsigned arithmetic that wraps its sub-zero readings,

```
stored = (((word - 320) & 0xFFFF) * 5 & 0xFFFF) // 9
```

Below 32 F, `word - 320` underflows and the stored value lands between about
713 and 728 C, which the boiler treats as warm outside. The largest value this
can produce is 7281 (728.1 C), nowhere near a negative C as a signed word, so
no written word can mean below freezing. Every readback in the live test
matches this, re-encoded with the read formula
`((stored * 9) & 0xFFFF) // 5 + 320` (e.g. 31.9 F reads back as 13425,
30.0 F as 13406). Fed values also truncate to 0.1 C. The boiler's own sensor
is fine below freezing; only the written path breaks. So Fahrenheit writes
below 32 F raise `ValueError`. Clamp to 32 F instead; a reset curve is
normally at its cap long before then. The other BMS writes (enable,
setpoints, rate) aren't implemented.

### Fahrenheit only, for now

Everything in this section was worked out on a boiler whose display is in
**Fahrenheit**:

- the units (tenths of a degree F);
- the conversion formula above;
- the 32 F limit;
- the ~5 minute hold.

A Fahrenheit board converts every written word from F to C, and that
conversion is what breaks below freezing.

A boiler set to **Celsius** should take signed tenths of a degree C as the
manual documents, with no conversion. So it may accept below-freezing values,
and its limits would differ. `encode_measured` has a Celsius branch (-40 to
60 C, signed tenths), but it has **not** been tested against a Celsius boiler,
and the Home Assistant integration doesn't handle that case at this time.
Treat Celsius writes as unsupported until someone checks one.

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
