# pylint: disable=W0621
"""Asynchronous Python client for the Fumis WiRCU API."""

import asyncio

from fumis import Fumis, StoveStatus


async def main() -> None:
    """Show example on controlling your Fumis WiRCU device."""
    async with Fumis(mac="AABBCCDDEEFF", password="1234") as fumis:
        info = await fumis.update_info()

        # Stove identity
        if info.controller.manufacturer:
            print(f"Stove: {info.controller.manufacturer} {info.controller.model_name}")

        # Status
        print(f"Status: {info.controller.stove_status.name}")

        # Temperature
        main_temp = info.controller.main_temperature
        if main_temp:
            print(f"Room: {main_temp.actual}° → {main_temp.setpoint}°")

        # Power
        pwr = info.controller.power
        print(f"Power: {pwr.kw} kW (level {pwr.set_power})")

        # Fuel
        fuel = info.controller.fuel()
        if fuel and fuel.quantity is not None:
            print(f"Fuel: {fuel.quantity_percentage:.0f}%")

        # Control the stove
        if info.controller.stove_status == StoveStatus.OFF:
            await fumis.set_target_temperature(23.0)


if __name__ == "__main__":
    asyncio.run(main())
