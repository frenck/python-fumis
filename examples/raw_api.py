# pylint: disable=W0621
"""Example: Get the raw API response for debugging or fixture capture."""

import asyncio
import json

from fumis import Fumis


async def main() -> None:
    """Fetch and print the unprocessed API response."""
    async with Fumis(mac="AABBCCDDEEFF", password="1234") as fumis:
        # Raw dict straight from the API (no model parsing)
        raw = await fumis.raw_status()

        # Pretty-print for inspection
        print(json.dumps(raw, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
