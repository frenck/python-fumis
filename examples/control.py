# pylint: disable=W0621
"""Asynchronous Python client for the Fumis WiRCU API."""

import asyncio

from fumis import Fumis


async def main(loop):
    """Show example on controlling your Fumis WiRCU device."""
    async with Fumis(mac="AABBCCDDEEFF", password="1234", loop=loop) as fumis:
        info = await fumis.update_info()
        print(info)

        await fumis.set_target_temperature(23.0)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(loop))
