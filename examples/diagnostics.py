# pylint: disable=W0621
"""Example: Access raw diagnostic variables and parameters."""

import asyncio

from fumis import Fumis


async def main() -> None:
    """Read diagnostic data from the stove controller."""
    async with Fumis(mac="AABBCCDDEEFF", password="1234") as fumis:
        info = await fumis.update_info()
        diag = info.controller.diagnostic

        # Convenience properties (None if not available on this stove)
        print(f"Fan 1 speed: {info.controller.fan1_speed}")
        print(f"Fan 2 speed: {info.controller.fan2_speed}")
        print(f"Exhaust temp: {info.controller.exhaust_temperature}")
        print(f"Pressure: {info.controller.pressure}")
        print(f"Door open: {info.controller.door_open}")

        # Stove model identification
        print(f"Stove model var: {info.controller.stove_model}")
        print(f"Parameter version var: {info.controller.parameter_version}")
        print(f"Model info: {info.controller.model_info}")

        # Raw access by ID (escape hatch for unlisted variables)
        rpm = diag.variable(34)
        print(f"F02 (var[34]): {rpm}")

        # Iterate all populated variables
        print("\nAll variables:")
        for var in diag.variables:
            if var.value != 0:
                print(f"  var[{var.id}] = {var.value}")

        # Parameters
        print("\nAll parameters:")
        for param in diag.parameters:
            print(f"  P{param.id:03d} = {param.value}")


if __name__ == "__main__":
    asyncio.run(main())
