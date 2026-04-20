# Python: Asynchronous client for the Fumis WiRCU API

[![GitHub Release][releases-shield]][releases]
[![Python Versions][python-versions-shield]][pypi]
![Project Stage][project-stage-shield]
![Project Maintenance][maintenance-shield]
[![License][license-shield]](LICENSE.md)

[![Build Status][build-shield]][build]
[![Code Coverage][codecov-shield]][codecov]
[![OpenSSF Scorecard][scorecard-shield]][scorecard]
[![Open in Dev Containers][devcontainer-shield]][devcontainer]

[![Sponsor Frenck via GitHub Sponsors][github-sponsors-shield]][github-sponsors]

[![Support Frenck on Patreon][patreon-shield]][patreon]

Asynchronous Python client for the Fumis WiRCU API.

## About

This package allows you to control and monitor Fumis WiRCU pellet stove
devices programmatically. It is mainly created to allow third-party programs
to automate the behavior of a Fumis WiRCU device.

An excellent example of this might be Home Assistant, which allows you to write
automations, to turn on your pellet stove and set a target temperature.

Known compatible stove brands:

- Austroflamm (Clou Duo, MO DUO, Polly 2.0)
- Heta (Green 200)
- HAAS+SOHN
- Eco Spar (Auriga, Solara, Tukana, Karina, Nova)
- Prity

## Installation

```bash
pip install fumis
```

To install with the optional CLI:

```bash
pip install "fumis[cli]"
```

## CLI

The optional CLI lets you control your stove directly from the terminal.
The `--mac` and `--password` options can also be set via the `FUMIS_MAC`
and `FUMIS_PASSWORD` environment variables.

```bash
# Set credentials once via environment variables
export FUMIS_MAC=AABBCCDDEEFF
export FUMIS_PASSWORD=1234

# Launch the live TUI dashboard
fumis

# Show device information
fumis info

# Turn the stove on/off
fumis on
fumis off

# Set target temperature
fumis temperature 23.5

# Set power level (1-5)
fumis power 3

# Enable/disable eco mode
fumis eco true

# Show weekly timer schedule / enable / disable
fumis timer
fumis timer true

# Sync the stove's clock to your system time
fumis sync-clock

# Show service diagnostics (sensors, IO, temperature channels)
fumis diagnostics

# Dump raw API response as JSON
fumis dump

# Emit machine-readable JSON
fumis info --json
```

The default command (no subcommand) launches a live TUI dashboard with
real-time temperature graphs, status display, and keyboard controls for
on/off, temperature, and power level.

## Usage

The client is an async context manager; every API call is a coroutine:

```python
import asyncio

from fumis import Fumis, StoveStatus


async def main() -> None:
    """Show example on controlling your Fumis WiRCU device."""
    async with Fumis(mac="AABBCCDDEEFF", password="1234") as fumis:
        info = await fumis.update_info()

        # Stove identity
        print(info.controller.manufacturer)  # "Austroflamm"
        print(info.controller.model_name)    # "Clou Duo"

        # Status
        print(info.controller.stove_status)  # StoveStatus.OFF
        print(info.controller.on)            # False

        # Temperatures
        main_temp = info.controller.main_temperature
        if main_temp:
            print(f"Room: {main_temp.actual}° → {main_temp.setpoint}°")

        # Combustion chamber
        print(info.controller.combustion_chamber_temperature)

        # Power
        print(f"{info.controller.power.kw} kW (level {info.controller.power.set_power})")

        # Door sensor
        print(f"Door open: {info.controller.door_open}")

        # Fuel level
        fuel = info.controller.fuel()
        if fuel:
            print(f"Fuel: {fuel.quantity_percentage}%")

        # Weekly timer schedule
        schedule = info.controller.schedule
        print(f"Timer: {'on' if info.controller.timer_enable else 'off'}")
        for prog in schedule.programs:
            if prog.active:
                print(f"  {prog}")  # "21:00-22:10"
        print(f"Active days: {schedule.active_days}")

        # Control the stove
        await fumis.turn_on()
        await fumis.set_target_temperature(23.0)
        await fumis.set_power(3)
        await fumis.set_eco_mode(enabled=True)
        await fumis.set_timer(enabled=True)
        await fumis.set_fan_speed(3)
        await fumis.set_clock()
        await fumis.turn_off()


if __name__ == "__main__":
    asyncio.run(main())
```

### Raw API access

For diagnostics, debugging, or fixture capture (useful for Home Assistant
diagnostic downloads):

```python
async with Fumis(mac="AABBCCDDEEFF", password="1234") as fumis:
    # Get the raw, unprocessed JSON dict from the API
    raw = await fumis.raw_status()
    print(json.dumps(raw, indent=2))
```

### Accessing diagnostic data

All diagnostic variables and parameters from the Fumis controller are
accessible via the structured model:

```python
info = await fumis.update_info()
c = info.controller

# Convenience properties (return None if not available)
c.exhaust_temperature     # Exhaust gas temp (var[11])
c.fan1_speed              # Fan 1 speed (var[4])
c.fan2_speed              # Fan 2 speed (var[12])
c.f02                     # F02 sensor input (var[34])
c.pressure                # Pressure sensor (var[35])
c.door_open               # Door sensor (var[33]) - True/False/None
c.stove_model             # Stove model ID (var[96])
c.parameter_version       # Parameter version (var[97])

# Raw diagnostic access (escape hatch)
c.diagnostic.variable(42)   # Any variable by ID → int | None
c.diagnostic.parameter(14)  # Any parameter by ID → int | None

# All temperature channels
for temp in c.temperatures:
    print(f"  Channel {temp.id}: {temp.actual}° (on screen: {temp.on_main_screen})")

# Iterate fans, fuels, etc.
for fan in c.fans:
    print(f"  Fan {fan.id}: speed {fan.speed}")
```

### Error handling

The exception hierarchy allows catching at any granularity:

```python
from fumis import (
    Fumis,
    FumisAuthenticationError,
    FumisConnectionError,
    FumisConnectionTimeoutError,
    FumisError,
    FumisResponseError,
    FumisStoveOfflineError,
)

try:
    async with Fumis(mac="AABBCCDDEEFF", password="1234") as fumis:
        await fumis.turn_on()
except FumisAuthenticationError:
    # Invalid MAC address or PIN (HTTP 401)
    ...
except FumisStoveOfflineError:
    # WiRCU not connected to cloud (HTTP 404)
    ...
except FumisConnectionTimeoutError:
    # Request timed out
    ...
except FumisConnectionError:
    # Any connectivity issue (timeout, DNS, HTTP error)
    ...
except FumisError:
    # Any Fumis-specific error
    ...
```

Exception hierarchy:

```
FumisError
├── FumisConnectionError
│   └── FumisConnectionTimeoutError
├── FumisResponseError
├── FumisAuthenticationError
└── FumisStoveOfflineError
```

### Enums

Status codes use proper Python enums, booleans where they make sense:

```python
from fumis import StoveStatus

info.controller.stove_status == StoveStatus.COMBUSTION  # True
info.controller.on                                      # True
info.controller.eco_mode.enabled                        # False

# Unknown values from the API are handled gracefully
StoveStatus(999)  # StoveStatus.UNKNOWN (never crashes)
```

## Changelog & Releases

This repository keeps a change log using [GitHub's releases][releases]
functionality. The format of the log is based on
[Keep a Changelog][keepchangelog].

Releases are based on [Semantic Versioning][semver], and use the format
of `MAJOR.MINOR.PATCH`. In a nutshell, the version will be incremented
based on the following:

- `MAJOR`: Incompatible or major changes.
- `MINOR`: Backwards-compatible new features and enhancements.
- `PATCH`: Backwards-compatible bugfixes and package updates.

## Contributing

This is an active open-source project. We are always open to people who want to
use the code or contribute to it.

We've set up a separate document for our
[contribution guidelines](CONTRIBUTING.md).

For in-depth API documentation and reverse engineering notes, see
[RESEARCH.md](RESEARCH.md).

Thank you for being involved! :heart_eyes:

## Setting up development environment

The easiest way to start, is by opening a CodeSpace here on GitHub, or by using
the [Dev Container][devcontainer] feature of Visual Studio Code.

[![Open in Dev Containers][devcontainer-shield]][devcontainer]

This Python project is fully managed using the [Poetry][poetry] dependency
manager. But also relies on the use of NodeJS for certain checks during
development.

You need at least:

- Python 3.11+
- [Poetry][poetry-install]
- NodeJS 24+ (including NPM)

To install all packages, including all development requirements:

```bash
npm install
poetry install
```

As this repository uses the [prek][prek] framework, all changes
are linted and tested with each commit. You can run all checks and tests
manually, using the following command:

```bash
poetry run prek run --all-files
```

To run just the Python tests:

```bash
poetry run pytest
```

## Authors & contributors

The original setup of this repository is by [Franck Nijhof][frenck].

For a full list of all authors and contributors,
check [the contributor's page][contributors].

## Disclaimer

This project is an independent, community-driven effort. It is **not
affiliated with, endorsed by, or supported by** Fumis (ATech elektronika
d.o.o.) or any stove manufacturer. All product names, trademarks, and
registered trademarks are property of their respective owners.

This library was developed by observing network traffic from devices we own,
using publicly available service manuals, and building on existing community
integrations. No access controls were bypassed and no proprietary code was
used. This work is done for interoperability purposes, protected under EU
law including the Software Directive (2009/24/EC), the Data Act (2023/2854),
and the GDPR. See [RESEARCH.md](RESEARCH.md) for the full legal basis and
methodology.

Use this software at your own risk. The authors are not responsible for any
damage to your stove, property, or person resulting from the use of this
library. Pellet stoves involve fire and heat; always follow your
manufacturer's safety guidelines.

## License

MIT License

Copyright (c) 2019-2026 Franck Nijhof

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

[build-shield]: https://github.com/frenck/python-fumis/actions/workflows/tests.yaml/badge.svg
[build]: https://github.com/frenck/python-fumis/actions/workflows/tests.yaml
[codecov-shield]: https://codecov.io/gh/frenck/python-fumis/branch/main/graph/badge.svg
[codecov]: https://codecov.io/gh/frenck/python-fumis
[contributors]: https://github.com/frenck/python-fumis/graphs/contributors
[devcontainer-shield]: https://img.shields.io/static/v1?label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode
[devcontainer]: https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/frenck/python-fumis
[frenck]: https://github.com/frenck
[github-sponsors-shield]: https://frenck.dev/wp-content/uploads/2019/12/github_sponsor.png
[github-sponsors]: https://github.com/sponsors/frenck
[keepchangelog]: http://keepachangelog.com/en/1.0.0/
[license-shield]: https://img.shields.io/github/license/frenck/python-fumis.svg
[maintenance-shield]: https://img.shields.io/maintenance/yes/2026.svg
[patreon-shield]: https://frenck.dev/wp-content/uploads/2019/12/patreon.png
[patreon]: https://www.patreon.com/frenck
[poetry-install]: https://python-poetry.org/docs/#installation
[poetry]: https://python-poetry.org
[prek]: https://github.com/frenck/prek
[project-stage-shield]: https://img.shields.io/badge/project%20stage-experimental-yellow.svg
[pypi]: https://pypi.org/project/fumis/
[python-versions-shield]: https://img.shields.io/pypi/pyversions/fumis
[releases-shield]: https://img.shields.io/github/release/frenck/python-fumis.svg
[releases]: https://github.com/frenck/python-fumis/releases
[scorecard]: https://scorecard.dev/viewer/?uri=github.com/frenck/python-fumis
[scorecard-shield]: https://api.scorecard.dev/projects/github.com/frenck/python-fumis/badge
[semver]: http://semver.org/spec/v2.0.0.html
