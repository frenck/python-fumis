# pylint: disable=W0621
"""Example: Read stove status and sensor data."""

import asyncio

from fumis import Fumis


async def main() -> None:
    """Read and display all available stove information."""
    async with Fumis(mac="AABBCCDDEEFF", password="1234") as fumis:
        info = await fumis.update_info()

        # Stove identity (if known)
        if info.controller.manufacturer:
            print(f"Stove: {info.controller.manufacturer} {info.controller.model_name}")

        # On/off and operational status
        print(f"On: {info.controller.on}")
        print(f"Status: {info.controller.stove_status.name}")

        # Room temperature
        main_temp = info.controller.main_temperature
        if main_temp:
            print(f"Room: {main_temp.actual}° (target: {main_temp.setpoint}°)")

        # Combustion chamber
        if info.controller.combustion_chamber_temperature is not None:
            print(f"Combustion: {info.controller.combustion_chamber_temperature}°")

        # Exhaust gas
        if info.controller.exhaust_temperature is not None:
            print(f"Exhaust: {info.controller.exhaust_temperature}°")

        # Power
        pwr = info.controller.power
        print(f"Power: {pwr.kw} kW (level {pwr.set_power})")

        # Fuel level
        fuel = info.controller.fuel()
        if fuel and fuel.quantity_percentage is not None:
            print(f"Fuel: {fuel.quantity_percentage:.0f}%")

        # Door sensor
        if info.controller.door_open is not None:
            print(f"Door open: {info.controller.door_open}")

        # WiRCU info
        print(f"WiRCU firmware: {info.unit.version}")
        print(f"Signal: {info.unit.signal_strength}%")

        # Statistics
        stats = info.controller.statistic
        print(f"Igniter starts: {stats.igniter_starts}")
        print(f"Uptime: {stats.uptime}")
        print(f"Heating time: {stats.heating_time}")


if __name__ == "__main__":
    asyncio.run(main())
