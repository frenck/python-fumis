# Fumis WiRCU API - Research & Programmer's Reference

Comprehensive technical reference for the Fumis WiRCU cloud API, compiled from
reverse engineering, service manuals, community integrations, and real device
fixtures.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
  - [Local Network Presence](#local-network-presence)
  - [Temperature Units](#temperature-units)
- [Cloud API Protocol](#cloud-api-protocol)
- [API Response Structure](#api-response-structure)
- [Status Codes (`controller.status`)](#status-codes)
- [State Codes (`controller.command`)](#state-codes)
- [Error Codes (`controller.error`)](#error-codes)
- [Alert Codes (`controller.alert`)](#alert-codes)
- [Temperature Channels](#temperature-channels)
- [Power Fields](#power-fields)
- [Fan Configuration](#fan-configuration)
- [Fuel Data](#fuel-data)
- [Eco Mode](#eco-mode)
- [Hybrid Mode](#hybrid-mode)
- [Antifreeze](#antifreeze)
- [Statistics](#statistics)
- [Diagnostic Parameters (P000-P105)](#diagnostic-parameters)
- [Diagnostic Variables](#diagnostic-variables)
- [Service Menu Structure](#service-menu-structure)
- [Known Write Commands](#known-write-commands)
- [Known Stove Brands Using Fumis](#known-stove-brands)
- [Known `stove_type` / `software_version` Values](#known-stove-identifiers)
- [Fixture Analysis: What Varies Between Stoves](#fixture-analysis)
- [Known Issues & Quirks](#known-issues)
- [Sources & References](#sources)

---

## Architecture Overview

Fumis (by ATech Electronics, Slovenia) manufactures combustion controllers
(the **Fumis Alpha** series) used as OEM components by many stove/boiler
manufacturers. The **WiRCU** is a WiFi gateway module that bridges the
stove's RS485 bus to the Fumis cloud.

```
┌─────────────┐   RS485   ┌───────────┐   WebSocket/TLS   ┌──────────────┐
│ Fumis Alpha │◄─────────►│  WiRCU    │◄─────────────────►│ api.fumis.si │
│ Controller  │           │  WiFi Box │                    │  Cloud API   │
└─────────────┘           └───────────┘                    └──────┬───────┘
                                                                  │
                                                           HTTPS REST API
                                                                  │
                                                           ┌──────┴───────┐
                                                           │  OEM Apps /  │
                                                           │  This Library│
                                                           └──────────────┘
```

**Important:** The WiRCU box does NOT validate TLS certificates when
connecting to `api.fumis.si`. This means local interception is possible
via DNS spoofing (see [ptwz/own_fumis][own_fumis]).

OEM stove brands ship their own mobile apps (e.g., Austroflamm PelletControl)
that talk to the same `api.fumis.si` backend. The generic Fumis app may
reject OEM devices ("Device not supported").

### Local Network Presence

The WiRCU module runs on a **TI CC3xxx SimpleLink** WiFi chip and exposes
a local web interface on **port 80** (`Server: WebServer V1.0`).

- **MAC OUI prefix:** `00:16:D0` (ATech elektronika d.o.o.)
- **Device name:** `WiRCU` (in the web config)
- **mDNS:** Not available (no mDNS/zeroconf services advertised)
- **Local web pages:** `/status.html`, `/dev_config.html`, `/ip_config.html`,
  `/profiles_config.html`, `/tools.html`
- **AJAX endpoints:** `/date_time_info.txt`, `/sys_up_time.txt`

For Home Assistant integration, **DHCP discovery** using the `00:16:D0` OUI
is the recommended discovery method. Any device with this MAC prefix on a
home network is almost certainly a WiRCU stove controller.

### Temperature Units

The API always returns temperatures in **Celsius**. The Celsius/Fahrenheit
toggle in the mobile app is a client-side display setting only - confirmed
by live testing (switching to Fahrenheit in the app does not change API values).

---

## Cloud API Protocol

### Base URL

```
https://api.fumis.si/v1/
```

### Authentication

All requests require these HTTP headers:

| Header       | Value                              |
| ------------ | ---------------------------------- |
| `username`   | MAC address (uppercase, no colons) |
| `password`   | PIN (printed on WiRCU box)         |
| `appname`    | Application name (arbitrary)       |
| `User-Agent` | Custom user agent string           |
| `Accept`     | `application/json`                 |

### Endpoints

| Method | Path           | Description                 |
| ------ | -------------- | --------------------------- |
| GET    | `/v1/status`   | Retrieve full device status |
| POST   | `/v1/status`   | Send commands to the stove  |

### Command Payload Structure (POST)

```json
{
  "unit": { "id": "<MAC>", "type": 0, "pin": "<PIN>" },
  "apiVersion": "1",
  "controller": { ... command data ... }
}
```

---

## API Response Structure

The GET `/v1/status` response has this top-level structure:

```json
{
  "apiVersion": "1.3",
  "unit": {
    "id": "AABBCCDDEEFF",
    "type": 3,
    "version": "2.5.0",
    "command": null,
    "rssi": "-48",
    "ip": "192.168.1.2",
    "timezone": null,
    "temperature": 26.5
  },
  "controller": {
    "type": 2,
    "version": "2.6.0",
    "command": 2,
    "status": 30,
    "heatingSlope": 0.2,
    "stoveLastAvailability": 1738739274,
    "mobileLastAvailability": 1738707975,
    "currentTime": 1738739291,
    "error": 0,
    "alert": 0,
    "timerEnable": false,
    "fuelType": 1,
    "timeToService": 2129,
    "delayedStartAt": -1,
    "delayedStopAt": -1,
    "power": { ... },
    "antifreeze": { ... },
    "statistic": { ... },
    "diagnostic": {
      "variables": [ ... ],
      "parameters": [ ... ],
      "timers": [ ... ]
    },
    "ecoMode": { ... },
    "hybrid": { ... } | null,
    "fans": [ ... ],
    "temperatures": [ ... ],
    "fuels": [ ... ],
    "timers": [ ... ]
  }
}
```

### Unit Fields

| Field         | Type         | Description                                    |
| ------------- | ------------ | ---------------------------------------------- |
| `id`          | `string`     | MAC address without colons (e.g. `AABBCCDDEEFF`) |
| `type`        | `int`        | Unit type (observed: 0, 3)                     |
| `version`     | `string`     | WiRCU firmware version                         |
| `command`     | `int\|null`  | Unknown; often `null`                          |
| `rssi`        | `string`     | WiFi RSSI in dBm (note: string, not int)       |
| `ip`          | `string`     | Local IP address of WiRCU box                  |
| `timezone`    | `null`       | Timezone (usually null)                        |
| `temperature` | `float\|null`| WiRCU box temperature (null on some devices)   |

### Controller Top-Level Fields

| Field                     | Type   | Description                                         |
| ------------------------- | ------ | --------------------------------------------------- |
| `type`                    | `int`  | Requested/selected mode (NOT the actual status)     |
| `version`                 | `string` | Controller firmware version                       |
| `command`                 | `int`  | Requested state: 1=off, 2=on                       |
| `status`                  | `int`  | Actual operational phase (see [Status Codes])       |
| `error`                   | `int`  | Error code (0=none, see [Error Codes])              |
| `alert`                   | `int`  | Alert/warning code (0=none, see [Alert Codes])      |
| `heatingSlope`            | `float`| Heating curve slope                                 |
| `currentTime`             | `int`  | Controller's current time (unix timestamp)          |
| `timerEnable`             | `bool` | Whether weekly timers are active                    |
| `fuelType`                | `int`  | Fuel type setting                                   |
| `timeToService`           | `int`  | Hours remaining until service (can be negative)     |
| `delayedStartAt`          | `int`  | Delayed start time (-1 = disabled)                  |
| `delayedStopAt`           | `int`  | Delayed stop time (-1 = disabled)                   |
| `stoveLastAvailability`   | `int`  | Last time stove was reachable (unix timestamp)      |
| `mobileLastAvailability`  | `int`  | Last time app connected (unix timestamp)            |

**Important distinction:** `controller.status` is the **actual runtime phase**.
`controller.type` appears to be the **requested/desired mode** and may not
always track `status`. Use `status` for the HA HVAC action state.

---

## Status Codes

`controller.status` - the actual operational phase of the stove.

| Code | Constant              | Description                         |
| ---- | --------------------- | ----------------------------------- |
| 0    | `off`                 | Stove is off                        |
| 1    | `cold_start_off`      | Cold start sequence ended (off)     |
| 2    | `wood_burning_off`    | Wood burning ended (off)            |
| 10   | `pre_heating`         | Pre-heating / heat-up phase         |
| 20   | `ignition`            | Ignition phase                      |
| 21   | `pre_combustion`      | Pre-combustion / ignition test      |
| 30   | `combustion`          | Active burning (normal operation)   |
| 40   | `eco`                 | Eco mode / burn wait                |
| 50   | `cooling`             | Cooling down after shutdown         |
| 60   | `hybrid_init`         | Hybrid mode initialization          |
| 80   | `hybrid_start`        | Hybrid mode starting                |
| 90   | `wood_start`          | Wood burning mode starting          |
| 100  | `cold_start`          | Cold start sequence                 |
| 110  | `wood_combustion`     | Active wood burning (hybrid stoves) |

Codes 60-110 only appear on **hybrid stoves** (wood + pellet, e.g.,
Austroflamm Clou Duo, MO DUO).

---

## State Codes

`controller.command` - the requested on/off state.

| Code | State     |
| ---- | --------- |
| 1    | `off`     |
| 2    | `on`      |

---

## Error Codes

`controller.error` - 0 means no error. Known codes from Fumis documentation:

| Code | Description                                                             |
| ---- | ----------------------------------------------------------------------- |
| 0    | No error                                                                |
| 101  | Ignition failed, water overtemperature or backfire protection           |
| 102  | Chimney/burning pot dirty, or manually stopped before flame detection   |
| 105  | Sensor T02 malfunction or disconnected                                  |
| 106  | Sensor T03 or T05 malfunction or disconnected                           |
| 107  | Sensor T04 malfunction or disconnected                                  |
| 108  | Security switch I01 tripped (STB). Reset and restart.                   |
| 109  | Pressure sensor switched OFF. Reset and restart.                        |
| 110  | Sensor T01 or T02 malfunction or disconnected                           |
| 111  | Sensor T01 or T03 malfunction or disconnected                           |
| 113  | Flue gases overtemperature. Clean chimney/heat exchanger.               |
| 114  | Fuel ignition timeout (empty burning pot) or tank empty (refuel)        |
| 115  | General error. Call service.                                            |

Additional error codes from the serial protocol (Palazzetti/Domochip):

| Code | Description       |
| ---- | ----------------- |
| 239  | MFDoor Alarm      |
| 240  | Fire Error        |
| 241  | Chimney Alarm     |
| 243  | Grate Error       |
| 244  | NTC2 Alarm        |
| 245  | NTC3 Alarm        |
| 247  | Door Alarm        |
| 248  | Pressure Alarm    |
| 249  | NTC1 Alarm        |
| 250  | TC1 Alarm         |
| 252  | Gas Alarm         |
| 253  | No Pellet Alarm   |

Note: The serial protocol codes (239+) may not appear through the cloud API.
They are included here for completeness since the underlying Fumis Alpha
controller uses them internally.

---

## Alert Codes

`controller.alert` - 0 means no active alert. Known codes:

| Code | ID   | Description                                                     |
| ---- | ---- | --------------------------------------------------------------- |
| 0    | -    | No alert                                                        |
| 1    | A001 | Low fuel level - refuel the tank                                |
| 2    | A002 | Service due - call for regular maintenance                      |
| 3    | A003 | Flue gas temperature warning - clean chimney/heat exchanger     |
| 4    | A004 | Low battery - call service for replacement                      |
| 5    | A005 | Speed sensor failure - call service                             |
| 6    | A006 | Door open - close the door                                      |
| 7    | A007 | Alternative operating mode, limited functionality (airflow sensor malfunction) |

Display format: the app shows `A00X` where X is the code value
(e.g., `controller.alert: 4` → "A004").

Additional non-critical codes from the Fumis Premium interface:

| Code | ID   | Description                                  |
| ---- | ---- | -------------------------------------------- |
| 2    | E002 | Infrared sensor malfunction                  |
| 3    | E003 | RF malfunction                               |
| 4    | E004 | Controller communication error               |

---

## Temperature Channels

`controller.temperatures[]` - array of temperature sensor entries.

### Entry Structure

```json
{
  "name": null,
  "weight": 0,
  "setType": 2,
  "actualType": 1,
  "onMainScreen": true,
  "actual": 22.1,
  "set": 24.0,
  "id": 1
}
```

| Field          | Type         | Description                                       |
| -------------- | ------------ | ------------------------------------------------- |
| `id`           | `int`        | Temperature channel identifier                    |
| `name`         | `string\|null` | Optional label (usually null)                   |
| `actual`       | `float`      | Current measured temperature                      |
| `set`          | `float`      | Target/setpoint temperature                       |
| `onMainScreen` | `bool`       | Whether shown on the stove's main display         |
| `actualType`   | `int`        | Sensor type (0=unused, 1=NTC, 10=TC thermocouple) |
| `setType`      | `int`        | Setpoint type (0=none, 1=internal, 2=user-adjustable) |
| `weight`       | `int`        | Display ordering weight                           |

### Known Temperature Channel IDs

| ID | Purpose                       | Notes                                          |
| -- | ----------------------------- | ---------------------------------------------- |
| 1  | Room / ambient temperature    | Primary controllable temp. `onMainScreen: true`, `actualType: 1`, `setType: 2` |
| 2  | Secondary (often unused)      | May be water temp on hydronic stoves           |
| 3  | Varies by stove               | Some hybrids show this on screen               |
| 4  | Varies                        | Usually inactive                               |
| 5  | Varies                        | Some hybrids show this on screen               |
| 6  | Usually inactive              |                                                |
| 7  | Combustion chamber temp       | `actualType: 10` (TC thermocouple). Confirmed on Austroflamm. |
| 8  | Eco mode restart threshold    | `set` = restart delta (e.g., 0.5°C)           |
| 9  | Eco mode stop threshold       | `set` = stop delta (e.g., 0°C)                |

### How to Find the Primary Temperature

The primary (room) temperature is the entry where:
- `onMainScreen` is `true` AND
- `actualType` > 0

This is more reliable than hardcoding `id=1`, as some stoves have
multiple on-screen temperatures (hybrids with weight-based ordering).

### Fumis Premium Named Channels

The Fumis Premium touchscreen interface refers to three temperature types:
- **AIR** - ambient/room temperature
- **ROOM 2** - second ambient (ducted systems)
- **WATER** - hydronic/boiler water temperature

Not all stoves support all three. Unsupported channels are hidden.

---

## Power Fields

`controller.power` object:

```json
{
  "setType": 1,
  "actualType": 2,
  "kw": 3.6,
  "actualPower": 1,
  "setPower": 5
}
```

| Field         | Type    | Description                                              |
| ------------- | ------- | -------------------------------------------------------- |
| `setPower`    | `int`   | User-set power level (1-5). **Writable.**                |
| `actualPower` | `int`   | Controller-acknowledged power level (mirrors `setPower`)  |
| `kw`          | `float` | Actual thermal output in kilowatts (lags behind level changes) |
| `setType`     | `int`   | Power setting type                                       |
| `actualType`  | `int`   | Actual power measurement type                            |

### Power field behavior (live tested)

Live testing on an Austroflamm Clou Duo revealed the exact semantics:

- **`setPower`** - the requested power level. Updates immediately when
  the command is sent.
- **`actualPower`** - the controller's acknowledged power level. Also
  updates immediately and mirrors `setPower`. Despite the name, this
  is NOT a real-time output measurement.
- **`kw`** - the actual thermal output in kilowatts. This **lags
  behind** power level changes as the controller adjusts pellet feed
  rate and airflow.

Observed during a level 5 → 2 → 5 transition:

```text
setPower=5  actualPower=0  kw=5.7   ← burning at level 5
setPower=2  actualPower=2  kw=5.7   ← command sent, kw hasn't changed yet
setPower=2  actualPower=2  kw=3.5   ← ~60s later, kw adjusted down
setPower=5  actualPower=5  kw=3.5   ← command sent, kw still at 3.5
setPower=5  actualPower=5  kw=5.7   ← later, kw ramps back up
```

**For HA integration:**
- Use `kw` as a **sensor** (actual thermal output)
- Use `setPower` as a **number entity** (1-5, writable)
- Don't expose `actualPower` as a separate entity - it just mirrors
  `setPower` and the name is misleading

The Fumis Premium interface allows switching between 5 power levels,
plus an optional AUTO mode that follows temperature modulation.

---

## Fan Configuration

`controller.fans[]` - array of fan entries:

```json
{
  "weight": 0,
  "speedType": 6,
  "speed": 1,
  "id": 1
}
```

| Field       | Type  | Description                                |
| ----------- | ----- | ------------------------------------------ |
| `id`        | `int` | Fan identifier (1 = primary exhaust fan)   |
| `speed`     | `int` | Current speed setting                      |
| `speedType` | `int` | Speed control type                         |
| `weight`    | `int` | Display ordering weight                    |

The Fumis Premium supports 5 ambient fan speed levels plus optional
"Hi" (max speed) and "AUTO" modes. Ducted stoves (Palazzetti) may
have FAN2-FAN4 for room distribution.

---

## Fuel Data

`controller.fuels[]` - array of fuel entries:

```json
{
  "name": null,
  "quality": 2,
  "qualityType": 0,
  "qualityActual": null,
  "quantitySetType": 2,
  "quantityActualType": 2,
  "quantity": 0.27,
  "quantityDisplay": 1,
  "id": 1
}
```

| Field              | Type         | Description                                |
| ------------------ | ------------ | ------------------------------------------ |
| `id`               | `int`        | Fuel entry ID (1 = primary)                |
| `quality`          | `int`        | Fuel quality setting (1-3)                 |
| `quantity`          | `float\|null` | Fuel level (0.0-1.0 scale, multiply by 100 for percentage) |
| `quantityDisplay`  | `int`        | Display mode for quantity                  |
| `qualityType`      | `int`        | Quality measurement type                   |
| `qualityActual`    | `null`       | Actual measured quality (usually null)     |

The Fumis Premium supports up to 3 quality levels for both pellets and
wood logs. Fuel autonomy monitoring (when enabled) predicts remaining
operating hours based on consumption.

---

## Eco Mode

`controller.ecoMode` object:

```json
{
  "ecoModeSetType": 1,
  "ecoModeEnable": 0
}
```

| Field            | Type       | Description                                |
| ---------------- | ---------- | ------------------------------------------ |
| `ecoModeEnable`  | `int\|null` | 0=off, 1=on (null if not supported)       |
| `ecoModeSetType` | `int\|null` | Eco mode type (-1 or null if not supported) |

When eco mode is active and the room temperature exceeds the setpoint,
the stove turns off automatically and restarts when temperature drops
below the setpoint. The restart and stop deltas are configured via
temperature channels 8 and 9 (see [Temperature Channels]).

---

## Hybrid Mode

`controller.hybrid` - only populated on hybrid (wood + pellet) stoves.
Pure pellet stoves return `null`.

```json
{
  "actualType": 1,
  "operation": 0,
  "state": 0
}
```

| Field        | Type  | Description                     |
| ------------ | ----- | ------------------------------- |
| `actualType` | `int` | Current hybrid mode type        |
| `operation`  | `int` | Current operation mode          |
| `state`      | `int` | Current hybrid state            |

**Known issue:** Some hybrid stove firmware returns a minimal object
`{"operation": 0}` instead of the full three fields.

---

## Antifreeze

`controller.antifreeze` object:

```json
{
  "temperature": 5,
  "enable": true
}
```

| Field         | Type         | Description                              |
| ------------- | ------------ | ---------------------------------------- |
| `temperature` | `float\|null` | Antifreeze trigger temperature          |
| `enable`      | `bool`       | Whether antifreeze protection is active  |

---

## Statistics

`controller.statistic` object:

```json
{
  "igniterStarts": 392,
  "uptime": 58184580,
  "heatingTime": 1823340,
  "serviceTime": 1823340,
  "overheatings": 0,
  "misfires": 0,
  "fuelQuantityUsed": 0
}
```

| Field              | Type  | Description                                         |
| ------------------ | ----- | --------------------------------------------------- |
| `igniterStarts`    | `int` | Total number of igniter starts (SC00)               |
| `overheatings`     | `int` | Total over-temperature events (SC01)                |
| `misfires`         | `int` | Total missed firings (SC02)                         |
| `uptime`           | `int` | Total powered-on time in **seconds** (SC03)         |
| `heatingTime`      | `int` | Total burning time in **seconds** (SC04)            |
| `serviceTime`      | `int` | Burning time since last service in **seconds** (SC05) |
| `fuelQuantityUsed` | `int` | Total fuel consumed (unit varies)                   |

---

## Diagnostic Parameters

`controller.diagnostic.parameters[]` - the P000-P105 operating parameters.

These are the **controller configuration parameters**, set during factory
programming or by a service technician. They are consistent in meaning
across all Fumis Alpha controllers - only the **values** differ per stove
model and power rating.

### Complete Parameter Table (P000-P105)

| ID  | Name                                    | Description / notes                                       |
| --- | --------------------------------------- | --------------------------------------------------------- |
| 0   | Fuel ignition timeout                   | Minutes. How long to attempt ignition.                    |
| 1   | Ignition test timeout                   | Minutes.                                                  |
| 2   | Fuel type                               | 0=pellet, other values for wood/combined                  |
| 3   | Heat up feeder OFF time                 | Deciseconds (÷10 for seconds)                             |
| 4   | Heat up feeder ON time                  | Deciseconds                                               |
| 5   | Fuel ignition feeder 1 OFF time         | Deciseconds                                               |
| 6   | Fuel ignition feeder 1 ON time          | Deciseconds                                               |
| 7   | Ignition test feeder 1 OFF time         | Deciseconds                                               |
| 8   | Ignition test feeder 1 ON time          | Deciseconds                                               |
| 9   | Power 1 feeder 1 OFF time              | Deciseconds. Pellet dosing at power level 1.              |
| 10  | Power 1 feeder 1 ON time              | Deciseconds                                               |
| 11  | Power 2 feeder 1 OFF time              | Deciseconds                                               |
| 12  | Power 2 feeder 1 ON time              | Deciseconds                                               |
| 13  | Power 3 feeder 1 OFF time              | Deciseconds                                               |
| 14  | Power 3 feeder 1 ON time              | Deciseconds                                               |
| 15  | Power 4 feeder 1 OFF time              | Deciseconds                                               |
| 16  | Power 4 feeder 1 ON time              | Deciseconds                                               |
| 17  | Power 5 feeder 1 OFF time              | Deciseconds                                               |
| 18  | Power 5 feeder 1 ON time              | Deciseconds                                               |
| 19  | Stop fire fan 1 speed                   | 0-255. Fan speed during shutdown.                         |
| 20  | Test fire fan 1 speed                   | 0-255                                                     |
| 21  | Heat up fan 1 speed                     | 0-255                                                     |
| 22  | Fuel ignition fan 1 speed               | 0-255                                                     |
| 23  | Ignition test fan 1 speed               | 0-255                                                     |
| 24  | Power 1 fan 1 speed                     | 0-255. Fan speed at power level 1.                        |
| 25  | Power 2 fan 1 speed                     | 0-255                                                     |
| 26  | Power 3 fan 1 speed                     | 0-255                                                     |
| 27  | Power 4 fan 1 speed                     | 0-255                                                     |
| 28  | Power 5 fan 1 speed                     | 0-255                                                     |
| 29-49 | _(additional feeder/fan params)_      | Vary by stove. Often 0 on simple stoves.                  |
| 50  | Modulation speed                        |                                                           |
| 51  | Modulation factor                       |                                                           |
| 52  | _(reserved)_                            |                                                           |
| 53  | Cool fluid entry temp. diff.            |                                                           |
| 54  | Ignition test gases temperature         | °C. Exhaust gas temp threshold for ignition test.         |
| 55  | Modulation start gases temperature      | °C                                                        |
| 56  | Heating device OFF gases temperature    | °C. Below this, stove shuts off.                          |
| 57  | Maximum (error) gases temperature       | °C. Above this, E113 overtemp error.                      |
| 58  | Fan 2 as ambient min. gases temp.       | °C                                                        |
| 59  | No fuel (error) gases temperature       | °C. Below this during burning → E114.                     |
| 60  | Fan 1 blow cleaning period              | Seconds. 0=disabled.                                      |
| 61  | Fan 1 blow cleaning duration            | Seconds                                                   |
| 62  | Fan 1 blow cleaning speed               | 0-255                                                     |
| 63  | Air pulse cleaning duration             |                                                           |
| 64  | Chamber cleaning duration/rotations     |                                                           |
| 65  | Ash extraction auger duration           |                                                           |
| 66  | Ash extraction auger period             |                                                           |
| 67  | ON temperature                          | °C. Stove ON threshold.                                   |
| 68  | OFF temp. / T1-T2 for max modul. speed  | °C                                                        |
| 69  | Anti-condensation exit temp.            | °C                                                        |
| 70  | Heat up duration                        | Seconds or minutes (varies by model)                      |
| 71  | Fuel ignition temp. check samples       | Number of samples                                         |
| 72  | Fuel ignition temperature rise          | °C rise required for ignition detection                   |
| 73  | User fuel feeder 1 ON time factor       | % (100 = nominal). User pellet dosing adjustment.         |
| 74  | User fuel fan 1 speed factor            | % (100 = nominal). User fan speed adjustment.             |
| 75  | Wood fuel fan 1 speed factor            | % (100 = nominal)                                         |
| 76  | Selected configuration                  | Stove configuration profile (1-N)                         |
| 77  | 2nd room temperature                    | Target temp for second room sensor                        |
| 78  | Flame ON level                          | Flame sensor threshold for "flame detected"               |
| 79  | Flame OFF level                         | Flame sensor threshold for "flame lost"                   |
| 80  | Flame OFF detection delay               | Seconds                                                   |
| 81  | Underpressure setpoint                  | Pa                                                        |
| 82  | Min. (error) underpressure/airflow      | Pa. Below this → error.                                   |
| 83  | Underpressure/airflow error delay       | Seconds                                                   |
| 84  | Accumulator temperature                 | °C                                                        |
| 85  | T1-T2 for water pump OFF               | °C differential                                           |
| 86  | Boiler to accumulator temperature drop  | °C                                                        |
| 87  | Keep fire fan 1 speed                   | 0-255. Fan speed during keep-fire (eco pause).            |
| 88  | Keep fire feeder 1 ON time             | Deciseconds                                               |
| 89  | Keep fire fan 1 duration                | Seconds                                                   |
| 90  | Keep fire period                        | Seconds                                                   |
| 91  | Feeder 2 delay / ON time factor         |                                                           |
| 92  | Pellets quality                         | 1-3. Default pellet quality setting.                      |
| 93  | Wood quality                            | 1-3. Default wood quality setting.                        |
| 94  | Time to service                         | Hours until next service.                                 |
| 95  | Stove cool fluid entry temp. diff.      | °C                                                        |
| 96  | Stove cool fluid exit temp. diff.       | °C                                                        |
| 97  | T1-T2 for min. modulation speed         | °C                                                        |
| 98  | Full level                              | Fuel tank full threshold                                  |
| 99  | Low level                               | Fuel tank low threshold (triggers A001)                   |
| 100 | Empty level                             | Fuel tank empty threshold                                 |
| 101 | Blow out duration                       | Seconds. Duration of post-shutdown fan blow.              |
| 102 | Antifreeze temperature                  | °C. Stove starts if temp drops below this.                |
| 103 | Water pump minimum speed                | RPM or PWM value                                          |
| 104 | Water pump maximum speed                | RPM or PWM value                                          |
| 105 | _(reserved)_                            |                                                           |

**Note:** Parameters P096 and P097 in this table are **controller
configuration** parameters (fluid temperature differentials), not the same
as diagnostic variables `var[96]` and `var[97]` which hold the software
version and stove type identifiers.

---

## Diagnostic Variables

`controller.diagnostic.variables[]` - runtime state values.

### Complete Variable ID Mapping

The following mapping was established through live testing, cross-referencing
with the PelletControl app's service info screen, and community fixtures.

| ID  | Description                          |
| --- | ------------------------------------ |
| 4   | Fan 1 speed                          |
| 5   | Current power level                  |
| 11  | Exhaust/flue gas temperature         |
| 12  | Fan 2 speed                          |
| 15  | Uptime                               |
| 17  | Heating time                         |
| 19  | Service time                         |
| 22  | Backwater temperature (hydronic)     |
| 23  | Controller clock: seconds            |
| 24  | Controller clock: minutes            |
| 25  | Controller clock: hours              |
| 26  | Day of week                          |
| 27  | Date: day                            |
| 28  | Date: month                          |
| 29  | Date: year                           |
| 30  | Digital input IO1 (STB thermostat)   |
| 31  | Digital input IO2                    |
| 32  | Digital input IO3                    |
| 33  | Digital input IO4 (door on Clou Duo) |
| 34  | F02 sensor input                     |
| 35  | Pressure sensor                      |
| 96  | Stove model identifier               |
| 97  | Parameter version                    |
| 98  | External thermostat enabled          |
| 99  | External thermostat contact state    |

### Error Log Structure

The error log stores up to 15 entries in diagnostic variables,
each as a group of 4 values:

| Entry | ID (error code) | Date | Time | Value |
| ----- | --------------- | ---- | ---- | ----- |
| 1     | var[36]         | var[38] | var[39] | var[37] |
| 2     | var[40]         | var[42] | var[43] | var[41] |
| 3     | var[44]         | var[46] | var[47] | var[45] |
| ...   | +4 per entry    |         |         |         |
| 15    | var[92]         | var[94] | var[95] | var[93] |

The pattern is: `ID, VAL, DATE, TIME` repeating every 4 variables
starting at var[36].

### Timer Structure

See [Diagnostic Timers](#diagnostic-timers) for the confirmed timer
layout (live-tested).

**Important:** The diagnostic variables array layout is consistent in its
**ID numbering** across stoves (var[34] is always F02 where present), but
some stoves may not populate all IDs. Missing/unused variables will have
value 0.

### Service Menu Analog Inputs (mapped to temperature sensors)

From the service manual's setting [10] "Ain":

| Service label | Description                  |
| ------------- | ---------------------------- |
| t01           | Exhaust/flue gas temperature |
| t02           | Water/boiler temperature     |
| t03           | Additional temp sensor       |
| t04           | Additional temp sensor       |
| t05           | Additional temp sensor       |
| Press         | Pressure sensor reading      |

### Service Menu Digital Inputs

From the service manual's setting [9] "din":

| Service label | Description        |
| ------------- | ------------------ |
| i01           | STB (safety thermostat) |
| i02           | Pressure switch    |
| i03           | Additional input   |
| i04           | Additional input   |

### Service Menu Digital Outputs

From the service manual's setting [11] "dout":

| Service label | Description                    |
| ------------- | ------------------------------ |
| o01-o07       | Output relays (heater, fans, motors, pump, etc.) |

---

## Service Menu Structure

The Fumis controller's service menu (accessed via display) has 13 items:

| Setting | Mark | Description                              |
| ------- | ---- | ---------------------------------------- |
| [1]     | -    | Lock display (OFF/Lo/Hi)                 |
| [2]     | -    | Display brightness (OFF, 1-5)            |
| [3]     | -    | Background display info (1=hour+temp, 2=temp, 3=hour) |
| [4]     | -    | Sound volume (1-5)                       |
| [5]     | -    | Temperature unit (°C/°F)                 |
| [6]     | Info | Device information                       |
| [7]     | -    | Unlock/Lock service settings (ON/OFF)    |
| [8]     | PAr  | Operating parameters P000-P105           |
| [9]     | din  | Digital input status (i01-i04)           |
| [10]    | Ain  | Analog input status (t01-t05, pressure)  |
| [11]    | dout | Manual output control (o01-o07)          |
| [12-13] | -    | _(locked, additional service functions)_  |

---

## Known Write Commands

Confirmed writable paths via the POST `/v1/status` endpoint:

| Command                  | `controller` payload                                          |
| ------------------------ | ------------------------------------------------------------- |
| Turn ON                  | `{"command": 2, "type": 0}`                                   |
| Turn OFF                 | `{"command": 1, "type": 0}`                                   |
| Set target temperature   | `{"temperatures": [{"set": <float>, "id": <int>}], "type": 0}` |
| Set power level          | `{"power": {"setPower": <1-5>}}`                               |
| Set eco mode             | `{"ecoMode": {"ecoModeEnable": <0\|1>}}`                      |
| Enable/disable timer     | `{"timerEnable": <true\|false>}`                               |
| Delayed start            | `{"delayedStartAt": <unix_timestamp\|-1>}`                     |
| Delayed stop             | `{"delayedStopAt": <unix_timestamp\|-1>}`                      |
| Set fan speed            | `{"fans": [{"id": <int>, "speed": <int>}]}`                   |
| Set fuel quality         | `{"fuels": [{"id": <int>, "quality": <int>}]}`                |
| Set fuel quantity display | `{"fuels": [{"id": <int>, "quantityDisplay": <int>}]}`       |
| Sync controller clock    | `{"diagnostic": {"variables": [{"id": 23, "value": <sec>}, {"id": 24, "value": <min>}, {"id": 25, "value": <hour>}, {"id": 26, "value": <dow>}, {"id": 27, "value": <day>}, {"id": 28, "value": <month>}, {"id": 29, "value": <year%100>}]}}` |

The `temperature_id` defaults to 1 (room temperature) but can be set to
other channel IDs for multi-zone control. Delayed start/stop use -1 to
clear a pending schedule.

---

## Known Stove Brands

### Using Fumis WiRCU (cloud API - what this library targets)

| Brand            | Confirmed stove models                      | Source                  |
| ---------------- | ------------------------------------------- | ----------------------- |
| **Austroflamm**  | Clou Duo, MO DUO, Polly 2.0                | User fixtures, issues   |
| **Heta**         | Green 200                                   | maheus/fumis_integration |
| **Eco Spar**     | Auriga, Solara, Tukana, Karina, Nova        | Service manual          |

### Using Fumis Alpha controller (serial protocol, different integration path)

| Brand            | Notes                                       |
| ---------------- | ------------------------------------------- |
| Palazzetti       | Uses Fumis Alpha 65 board                   |
| Jotul            | Palazzetti-distributed                      |
| TurboFonte       | Palazzetti-distributed                      |
| Godin            | Palazzetti-distributed                      |
| Fonte Flamme     | Palazzetti-distributed                      |
| Invicta          | Palazzetti-distributed                      |

**Note:** Rika is the parent company of Austroflamm. Some Rika stoves
may use WiRCU, but this is unconfirmed.

---

## Known Stove Identifiers

From `diagnostic.variables[96]` (software version) and
`diagnostic.variables[97]` (stove type):

| `var[96]` | `var[97]` | Brand / Model                       | Source          |
| --------- | --------- | ----------------------------------- | --------------- |
| 211       | 15        | Austroflamm Clou Duo (hybrid, 7kW)  | janosch1337, live testing |
| 2         | 12        | Unknown hybrid stove (2.7kW)        | Issue #5 (dirkclae) |
| 2         | 10        | Unknown pellet-only stove (3.6kW)   | Issue #20 (adrien-parasote) |
| -         | -         | Not populated / older firmware      | Original fixture (fw <1.7) |

**Notes:**
- `var[96]` alone does NOT uniquely identify the stove - the `var[96]=2`
  value appears on at least two different stove types (pellet-only and
  hybrid) with different `var[97]` values.
- Both var[96] and var[97] together form the stove identity.
- Older firmware (controller version < 1.7, like the original fixture)
  may not populate var[96]/var[97] at all - the diagnostic variables
  array may be shorter than 96 entries.
- The PelletControl app labels var[96] as "Software versie" and var[97]
  as "Type kachel".

---

## Fixture Analysis: What Varies Between Stoves

Based on comparing fixtures from an Austroflamm Clou Duo (hybrid) and an
unknown pellet-only stove:

### Consistent across all stoves (safe to parse generically)

- Top-level controller fields (`status`, `command`, `error`, `alert`, etc.)
- `power` object structure and field names
- `statistic` object structure
- `ecoMode` object structure
- `fans[]` array structure
- `fuels[]` array structure
- `temperatures[]` array structure and self-describing fields
- Status code meanings (0-50 are universal; 60-110 are hybrid-only)
- Command structure for writes (same POST format)

### Varies by stove model

- **Number of active temperature channels** - simple stoves may have
  only id=1 active; hydronic stoves add water temp; hybrids have more
- **Combustion chamber temp location** - sometimes `temperatures[id=7]`,
  sometimes only in `diagnostic.variables[11]`
- **Diagnostic variable population** - some vars are 0 on stoves
  without the corresponding sensor
- **`hybrid` field** - `null` on pellet-only stoves, populated on hybrids
- **`unit.temperature`** - `null` on some units, populated on others
- **`antifreeze`** - `temperature: null` on stoves without this feature
- **Fan count and speed types** - varies with stove complexity

### NOT brand-specific (same IDs across brands)

- Parameter IDs (P000-P105) - same meaning everywhere, values differ
- Temperature channel IDs (id=1=room, id=7=combustion, id=8/9=eco thresholds)

### CONFIRMED brand-specific (variable IDs differ per stove type)

Live testing against an Austroflamm Clou Duo (stove_type=15) and
cross-referencing with the PelletControl app service screen during
multiple phases (idle, ignition, combustion, cooling) revealed:

| Variable | Meaning (stove type 15)                            | App field                          |
| -------- | -------------------------------------------------- | ---------------------------------- |
| var[34]  | **Fan RPM** (Ventilator 1 snelheid / Invoer F02)   | 893-1152 during operation          |
| var[35]  | **Luchtdruk** (air pressure)                        | 700-710 during cooling             |

The PelletControl app shows "Ventilator 1 snelheid" and "Invoer F02"
as the same value (both read from the same sensor). Exact values
between our API polls and the app may differ slightly due to poll
timing - these readings change rapidly during phase transitions.

For stove type 10 (issue #20), the same variable IDs appear to hold
the same types of readings (var[34]=1347 RPM, var[35]=608 pressure).

**Note:** Initial testing incorrectly suggested these were swapped
between stove types. Careful cross-referencing against app screenshots
during cooling phase (where values change slowly) confirmed they are
consistent: **var[34]=fan RPM, var[35]=pressure across both stove types.**

### Diagnostic variable `var[4]` - exhaust gas temperature

Live polling during ignition revealed `var[4]` is the **exhaust gas
temperature** (rookgastemperatuur). It was 0 when the stove was off,
ramped to ~121 during ignition, then settled to ~92-95 during stable
combustion. This matches the service manual's analog input t01
(exhaust/flue gas temperature).

### Digital inputs IO1-IO4 (Austroflamm Clou Duo, stove type 15)

Live tested by physically opening/closing the stove door while polling:

| Input | Variable   | Meaning                | Idle state | Notes                          |
| ----- | ---------- | ---------------------- | ---------- | ------------------------------ |
| IO1   | `var[30]`  | STB safety thermostat  | 1 (OK)     | Always ON unless tripped       |
| IO2   | `var[31]`  | Igniter/fan relay      | 0 (OFF)    | ON during burning phases       |
| IO3   | `var[32]`  | Unknown / unused       | 0           | Always OFF during all tests. Could be ash door on some models - untested. |
| IO4   | `var[33]`  | **Combustion door**    | 1 (closed)  | 0=open, 1=closed. Confirmed by physical test. |

The combustion door sensor (`var[33]`) provides a clean binary signal
with no bouncing - suitable for a HA binary sensor entity.

### Ash dump lever - no electronic sensor

The ash dump lever at the bottom of the Clou Duo is purely mechanical.
Opening it does not trigger any IO input change. However, the air
pressure sensor (`var[35]`) reacts to the draft change (jumped from
31 to 101 when the lever was opened), so it could theoretically be
inferred - but not reliably.

### Pellet reservoir lid - no electronic sensor

The pellet hopper lid on top is also purely mechanical. Opening it
does not trigger any IO or variable change. The fuel level is tracked
by consumption calculation, not by physical sensing.

### Diagnostic variable `var[31]` - igniter relay (IO2)

`var[31]` (IO2) switched from OFF to ON during ignition. The
PelletControl app confirmed "Invoer IO2: OFF" when idle and ON during
startup. This is the **igniter element relay** - it stays ON through
ignition and into combustion until the flame is confirmed stable.

---

## Startup Sequence (Live Observed)

The full startup sequence was captured by polling an Austroflamm Clou
Duo every 30 seconds during ignition. The status codes progress as:

```text
status  0 (off)             → stove idle, combustion chamber ~21°
status 10 (pre_heating)     → igniter warming up
status 20 (ignition)        → pellets catching fire, combustion ~148°, exhaust ~98°
status 21 (pre_combustion)  → flame detection test, combustion ~169°, exhaust ~121°
status 30 (combustion)      → stable burning, combustion ~190°, exhaust settling ~92°
```

### Status code to PelletControl app label mapping

| Status | Constant         | PelletControl (NL) | PelletControl (EN)     |
| ------ | ---------------- | ------------------ | ---------------------- |
| 0      | `off`            | Uit                | Off                    |
| 10     | `pre_heating`    | Opstartfase 1      | Startup phase 1        |
| 20     | `ignition`       | Opstartfase 2      | Startup phase 2        |
| 21     | `pre_combustion` | _(transition)_     | _(transition)_         |
| 30     | `combustion`     | Verbranding        | Combustion             |
| 40     | `eco`            | Eco                | Eco                    |
| 50     | `cooling`        | Afkoelen           | Cooling                |

### Observations during ignition

- The ignition-to-combustion transition takes approximately **90-120
  seconds** once pellets catch fire.
- **Fan/pressure values peak during ignition** then settle: luchtdruk
  dropped from 1368 (peak airflow) to 1052 (stable combustion), fan2
  from 1077 to 688. The controller reduces air intake once a stable
  flame is established.
- `heatingTime` and `serviceTime` tick together and appear to track
  the same value (both reset on service).
- `igniterStarts` did not increment for this startup - it may only
  count after a full cool-down cycle, or it tracks total starts from
  factory.

---

## Known Issues

1. **Trailing slash on POST** - POST to `/v1/status` may return 301
   redirect. POST to `/v1/status/` (with trailing slash) works reliably.

2. **Command latency** - changes may take 2-5 minutes to apply after a
   successful API response (the cloud relays to the WiRCU on its next
   poll cycle).

3. **No TLS certificate validation** - the WiRCU box accepts any host
   that resolves as `api.fumis.si`, enabling local interception.

4. **OEM app restrictions** - the generic Fumis app may reject
   OEM-branded devices. OEM apps (Austroflamm PelletControl, etc.) work.

5. **Hybrid stove status codes** - status codes 60-110 (hybrid/wood
   modes) were missing from older implementations, causing the stove to
   show as "off" during wood burning.

6. **`kw` vs `actualPower` confusion** - `kw` is the nominal output
   and may remain non-zero when off. `actualPower` better reflects
   real-time state. Issue #18 in maheus/fumis_integration.

7. **RPM/pressure swap** - the original vendorized copy had
   `var[34]` as pressure and `var[35]` as RPM (swapped). Issue #20
   confirmed the correct mapping: **var[34]=RPM, var[35]=pressure**.

8. **`rssi` is a string** - the API returns `rssi` as a string
   (e.g., `"-48"`), not an integer. Must be cast.

9. **`controller.command` vs `controller.status` mismatch** - a stove
   can have `command: 2` (on) while `status: 0` (off). This happens
   when the stove was requested to turn on but hasn't entered
   pre-heating yet, or when an error prevents startup. Always use
   `status` for the actual operational phase.

10. **Controller clock not NTP-synced** - the controller's internal
    clock may show 01/01/2000 for timestamps (error history, etc.)
    if NTP is not configured. The `currentTime` field in the API
    response IS a real unix timestamp from the cloud, not the
    controller clock.

11. **Internal vs cloud error codes** - the cloud API reports E102
    but the diagnostic variables store error 241 (Chimney Alarm from
    the Fumis Alpha serial protocol). The cloud-facing error codes
    (E1xx) may be a remapped subset of the internal codes (2xx).

---

## Error History in Diagnostic Variables

Error history is stored in `diagnostic.variables` as repeating groups
of 4 values. Observed pattern on an Austroflamm Clou Duo with 3x E102:

```
var[37] = 241         ← internal error code (241 = Chimney Alarm)
var[38] = 20000101    ← date (YYYYMMDD, 01/01/2000 = clock not set)
var[39] = 8           ← time or additional data
var[40] = 1           ← sequence number

var[41] = 241         ← error 2
var[42] = 20000101
var[43] = 10
var[44] = 2

var[45] = 241         ← error 3
var[46] = 20000101
var[47] = 2347
var[48] = 3
```

The PelletControl app's "Historiek fouten" (error history) screen
displays these as "Fout - E102" with timestamps from the controller.

---

## Diagnostic Timers

`diagnostic.timers[]` contains the weekly timer schedule data. The
`controller.timers` array is separate (and typically empty), while
`diagnostic.timers` holds the raw timer configuration with 51 entries
(timer[0]-timer[50]).

The master enable/disable is `controller.timerEnable` (boolean).

### Confirmed structure (live-tested on Austroflamm Clou Duo)

**Timer programs** - 4 slots of (ON hour, ON minute, OFF hour, OFF minute):

| Timer | ON hour | ON min | OFF hour | OFF min | Temperature |
| ----- | ------- | ------ | -------- | ------- | ----------- |
| Prog 1 | timer[0] | timer[1] | timer[2] | timer[3] | timer[45] |
| Prog 2 | timer[4] | timer[5] | timer[6] | timer[7] | timer[46] |
| Prog 3 | timer[8] | timer[9] | timer[10] | timer[11] | timer[47] |
| Prog 4 | timer[12] | timer[13] | timer[14] | timer[15] | timer[48] |

**Day-of-week enables** - each day has a pair (slot 1 enable, slot 2 enable):

| Day | Slot 1 | Slot 2 |
| --- | ------ | ------ |
| Monday | timer[16] | timer[17] |
| Tuesday | timer[18] | timer[19] |
| Wednesday | timer[20] | timer[21] |
| Thursday | timer[22] | timer[23] |
| Friday | timer[24] | timer[25] |
| Saturday | timer[26] | timer[27] |
| Sunday | timer[28] | timer[29] |

A value of 1 = enabled, 0 = disabled.

**Live example** - schedule 21:00-22:10 on Monday-Friday:

```
timer[0]=21  timer[1]=0   timer[2]=22  timer[3]=10   ← 21:00-22:10
timer[16]=1  timer[18]=1  timer[20]=1  timer[22]=1  timer[24]=1  ← Mon-Fri
timer[26]=0  timer[28]=0                                          ← Sat-Sun off
timer[45]=200                                                     ← temperature (÷10 = 20.0°?)
```

**Write command** to toggle timers:

```json
{"timerEnable": true}   // enable
{"timerEnable": false}  // disable
```

---

## Polling and Update Cycle

From live testing, the cloud API returns fresh data roughly every
**30 seconds** (matching the WiRCU's update cycle to the cloud).

For the HA integration, a **30-second scan interval** is recommended.
Polling faster is pointless since the cloud data only updates every
~30s anyway.

After sending a command, there is a brief delay before the stove
responds - the command propagates through the cloud to the WiRCU.

### API Error Responses

The API returns errors as JSON with `code` (int) and `message` (string):

```json
{"message": "A unit controller with that mac and pin doesn't exist", "code": 401}
{"message": "Stove not connected", "code": 404}
{"statusCode": 500, "message": "Internal server error"}
```

Three error categories are relevant for consumers:

| Category | HTTP Status | Meaning |
| --- | --- | --- |
| Authentication | 401 | Invalid MAC/PIN |
| Stove offline | 404 | WiRCU not connected to cloud |
| Server error | 5xx | Cloud API issue |

The stove can also be "offline" when the WiRCU loses WiFi
connectivity or is powered off.

---

## Sources

### Repositories

| Repository | Description |
| --- | --- |
| [frenck/python-fumis][python-fumis] | This library |
| [maheus/fumis_integration][maheus] | HA custom component (HACS) with vendorized client |
| [janosch1337/fumis_integration_clou_duo][janosch] | Fork with Clou Duo fixture and hybrid additions |
| [ptwz/own_fumis][own_fumis] | Local WebSocket-to-MQTT bridge for self-hosting |
| [Domochip/WPalaControl][wpalac] | ESP8266 replacement for Palazzetti ConnectionBox (serial) |
| [Domochip/Palazzetti][palazzetti] | C++ library for Fumis/Palazzetti serial protocol |
| [edeweerdt/jeedom_heta][jeedom] | Jeedom plugin for Heta/Austroflamm via WiRCU |

### Documentation

| Document | URL |
| --- | --- |
| Fumis Alpha errors and alerts | <https://www.fumis.solutions/s/u/Fumis_Alpha_errors_and_alerts_web.pdf> |
| Fumis Premium User Guide | <https://www.svt.ee/product_extra_files/FUMIS_Premium%20user%20interface_UG_EN_V1-0_013.pdf> |
| Fumis Alpha V2 datasheet | <https://www.fumis.solutions/s/u/ALPHAV2.pdf> |
| Service manual (pellet boilers/stoves) | <https://cdn.contentspeed.ro/pimromstal.websales.ro/cs-content/cs-docs/products/34ts0014manualtehnicintrorig_55461_10_1676703733.pdf> |
| Fumis WiRCU manual (Manualslib) | <https://www.manualslib.com/manual/2102460/Fumis-Wircu.html> |
| Austroflamm WiRCU-BOX manual | <https://www.manualslib.com/manual/3684134/Austroflamm-Wircu-Box.html> |
| Peter Turczak's reverse engineering notes | <https://peter.turczak.de/content/projects/fumis/> |

### Community Issues (with useful fixtures/data)

| Issue | Key data |
| --- | --- |
| [maheus#17][i17] | Hybrid stove status codes, Clou Duo fixture, wood mode detection |
| [maheus#20][i20] | RPM/pressure variable ID confirmation, full fixture from unknown brand |
| [maheus#18][i18] | kW vs actualPower behavior on Austroflamm Clou |
| [maheus#5][i5] | Multiple temperature channels on hybrid stoves |

[python-fumis]: https://github.com/frenck/python-fumis
[maheus]: https://github.com/maheus/fumis_integration
[janosch]: https://github.com/janosch1337/fumis_integration_clou_duo
[own_fumis]: https://github.com/ptwz/own_fumis
[wpalac]: https://github.com/Domochip/WPalaControl
[palazzetti]: https://github.com/Domochip/Palazzetti
[jeedom]: https://edeweerdt.github.io/jeedom_heta/fr_FR/
[i17]: https://github.com/maheus/fumis_integration/issues/17
[i20]: https://github.com/maheus/fumis_integration/issues/20
[i18]: https://github.com/maheus/fumis_integration/issues/18
[i5]: https://github.com/maheus/fumis_integration/issues/5
