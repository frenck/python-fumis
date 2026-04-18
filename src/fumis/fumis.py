"""Asynchronous Python client for the Fumis WiRCU API."""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Self

import aiohttp
import orjson
from yarl import URL

from .exceptions import (
    FumisAuthenticationError,
    FumisConnectionError,
    FumisConnectionTimeoutError,
    FumisError,
    FumisResponseError,
    FumisStoveOfflineError,
)
from .models import FumisInfo

if TYPE_CHECKING:
    from datetime import datetime

_LOGGER = logging.getLogger(__name__)


@dataclass
class Fumis:
    """Main class for handling connections with the Fumis WiRCU API."""

    mac: str = field(repr=False)
    password: str = field(repr=False)
    request_timeout: int = 60
    session: aiohttp.ClientSession | None = None

    info: FumisInfo | None = field(default=None, init=False)
    _close_session: bool = field(default=False, init=False)

    async def _request(
        self,
        uri: str = "",
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle a request to the Fumis WiRCU API."""
        url = URL.build(
            scheme="https", host="api.fumis.si", port=443, path="/v1/"
        ).join(URL(uri))

        if self.session is None:
            self.session = aiohttp.ClientSession()
            self._close_session = True

        _LOGGER.debug("%s %s", method, url)

        try:
            async with self.session.request(
                method,
                url,
                json=data,
                headers={
                    "Accept": "application/json",
                    "password": self.password,
                    "User-Agent": "PythonFumis",
                    "username": self.mac,
                },
                timeout=aiohttp.ClientTimeout(total=self.request_timeout),
            ) as response:
                _LOGGER.debug("%s %s returned %s", method, url, response.status)

                if response.status == 401:
                    msg = "Invalid MAC address or PIN"
                    raise FumisAuthenticationError(msg)

                if response.status == 404:
                    msg = "Stove not connected"
                    raise FumisStoveOfflineError(msg)

                response.raise_for_status()

                content_type = response.headers.get("Content-Type", "")
                if "application/json" not in content_type:
                    text = await response.text()
                    msg = "Unexpected response from the Fumis WiRCU API"
                    raise FumisResponseError(
                        msg,
                        {"Content-Type": content_type, "response": text},
                    )

                return orjson.loads(await response.read())  # pylint: disable=no-member
        except FumisError:  # pylint: disable=try-except-raise
            raise
        except TimeoutError as exception:
            _LOGGER.debug("Timeout connecting to %s", url)
            msg = "Timeout occurred while connecting to the Fumis WiRCU API"
            raise FumisConnectionTimeoutError(msg) from exception
        except aiohttp.ClientResponseError as exception:
            _LOGGER.debug("Response error for %s: %s", url, exception)
            msg = "Error response from the Fumis WiRCU API"
            raise FumisResponseError(msg) from exception
        except (
            aiohttp.ClientError,
            socket.gaierror,
        ) as exception:
            _LOGGER.debug("Connection error for %s: %s", url, exception)
            msg = "Error occurred while communicating with the Fumis WiRCU API"
            raise FumisConnectionError(msg) from exception

    async def _send_command(self, data: dict[str, Any]) -> None:
        """Send a command to the Fumis WiRCU device."""
        _LOGGER.debug("Sending command: %s", data)
        command_data = {
            "unit": {"id": self.mac, "type": 0, "pin": self.password},
            "apiVersion": "1",
            "controller": data,
        }
        await self._request("status", method="POST", data=command_data)

    async def update_info(self) -> FumisInfo:
        """Get all information about the Fumis WiRCU device."""
        try:
            data = await self._request("status")
        except FumisError:
            self.info = None
            raise

        self.info = FumisInfo.from_dict(data)
        _LOGGER.debug(
            "Updated info: status=%s, temp=%s",
            self.info.controller.stove_status.name,
            self.info.controller.main_temperature.actual
            if self.info.controller.main_temperature
            else None,
        )
        return self.info

    async def raw_status(self) -> dict[str, Any]:
        """Return the raw API response from GET /v1/status.

        Useful for diagnostics, debugging, and fixture capture.
        The response is the unprocessed JSON dict from the API.
        """
        return await self._request("status")

    async def turn_on(self) -> None:
        """Turn on Fumis WiRCU device."""
        await self._send_command({"command": 2, "type": 0})

    async def turn_off(self) -> None:
        """Turn off Fumis WiRCU device."""
        await self._send_command({"command": 1, "type": 0})

    async def set_target_temperature(
        self, temperature: float, temperature_id: int = 1
    ) -> None:
        """Set target temperature of Fumis WiRCU device."""
        await self._send_command(
            {"temperatures": [{"set": temperature, "id": temperature_id}], "type": 0}
        )

    async def set_power(self, power: int) -> None:
        """Set power level of Fumis WiRCU device."""
        await self._send_command({"power": {"setPower": power}})

    async def set_eco_mode(self, *, enabled: bool) -> None:
        """Set eco mode on/off for Fumis WiRCU device."""
        await self._send_command({"ecoMode": {"ecoModeEnable": int(enabled)}})

    async def set_timer(self, *, enabled: bool) -> None:
        """Enable or disable the weekly timer schedule."""
        await self._send_command({"timerEnable": enabled})

    async def set_delayed_start(self, at: datetime | None) -> None:
        """Schedule a one-off delayed start, or clear it.

        Pass a datetime to schedule the stove to turn on at that time,
        or None to cancel a pending delayed start.
        """
        value = -1 if at is None else int(at.timestamp())
        await self._send_command({"delayedStartAt": value})

    async def set_delayed_stop(self, at: datetime | None) -> None:
        """Schedule a one-off delayed stop, or clear it.

        Pass a datetime to schedule the stove to turn off at that time,
        or None to cancel a pending delayed stop.
        """
        value = -1 if at is None else int(at.timestamp())
        await self._send_command({"delayedStopAt": value})

    async def set_clock(self) -> None:
        """Sync the controller clock to the current local time.

        Sets the controller's internal RTC via diagnostic variables
        (var[23]-var[29]). The controller uses local time for timer
        schedules and error log timestamps.
        """
        from datetime import (  # noqa: PLC0415 # pylint: disable=import-outside-toplevel
            UTC,
            datetime,
        )

        now = datetime.now(UTC).astimezone()
        await self._send_command(
            {
                "diagnostic": {
                    "variables": [
                        {"id": 23, "value": now.second},
                        {"id": 24, "value": now.minute},
                        {"id": 25, "value": now.hour},
                        {"id": 26, "value": now.isoweekday()},
                        {"id": 27, "value": now.day},
                        {"id": 28, "value": now.month},
                        {"id": 29, "value": now.year % 100},
                    ]
                }
            }
        )

    async def set_fan_speed(self, speed: int, fan_id: int = 1) -> None:
        """Set fan speed."""
        await self._send_command({"fans": [{"id": fan_id, "speed": speed}]})

    async def set_fuel_quality(self, quality: int, fuel_id: int = 1) -> None:
        """Set fuel quality level."""
        await self._send_command({"fuels": [{"id": fuel_id, "quality": quality}]})

    async def set_fuel_quantity_display(self, display: int, fuel_id: int = 1) -> None:
        """Set fuel quantity display mode."""
        await self._send_command(
            {"fuels": [{"id": fuel_id, "quantityDisplay": display}]}
        )

    async def close(self) -> None:
        """Close open client session."""
        if self.session and self._close_session:
            await self.session.close()

    async def __aenter__(self) -> Self:
        """Async enter."""
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        """Async exit."""
        await self.close()
