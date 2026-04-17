# pylint: disable=W0621
"""Example: Robust error handling for all failure modes."""

import asyncio

from fumis import (
    Fumis,
    FumisAuthenticationError,
    FumisConnectionError,
    FumisConnectionTimeoutError,
    FumisResponseError,
    FumisStoveOfflineError,
)


async def main() -> None:
    """Demonstrate catching specific error types."""
    try:
        async with Fumis(mac="AABBCCDDEEFF", password="1234") as fumis:
            info = await fumis.update_info()
            print(f"Status: {info.controller.stove_status.name}")

    except FumisAuthenticationError:
        # Invalid MAC address or PIN (HTTP 401)
        print("Bad credentials - check MAC and PIN")

    except FumisStoveOfflineError:
        # WiRCU not connected to cloud (HTTP 404)
        print("Stove is offline - check WiFi on the WiRCU")

    except FumisConnectionTimeoutError:
        # Request timed out
        print("Connection timed out - API may be down")

    except FumisResponseError:
        # Server returned an error (5xx) or unexpected content
        print("Bad response from API")

    except FumisConnectionError:
        # Any other connectivity issue (DNS, network)
        print("Network error - check internet connection")


if __name__ == "__main__":
    asyncio.run(main())
