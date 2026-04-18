"""Constants for the Fumis WiRCU API."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Any


class StoveStatus(IntEnum):
    """Stove operational status (from controller.status)."""

    OFF = 0
    """Stove is off and idle."""

    COLD_START_OFF = 1
    """Stove turned off after a cold start attempt."""

    WOOD_BURNING_OFF = 2
    """Stove turned off after wood burning."""

    PRE_HEATING = 10
    """Warming up before ignition."""

    IGNITION = 20
    """Igniter is active, starting the fire."""

    PRE_COMBUSTION = 21
    """Fire is catching, transitioning to stable combustion."""

    COMBUSTION = 30
    """Normal pellet combustion, stove is heating."""

    ECO = 40
    """Eco mode active, reduced output to maintain temperature."""

    COOLING = 50
    """Stove is cooling down after being turned off."""

    HYBRID_INIT = 60
    """Hybrid mode initializing (wood + pellet stoves)."""

    HYBRID_START = 80
    """Hybrid mode starting combustion."""

    WOOD_START = 90
    """Wood-only combustion starting."""

    COLD_START = 100
    """Cold start sequence (extended ignition for cold stove)."""

    WOOD_COMBUSTION = 110
    """Wood-only combustion active."""

    UNKNOWN = -1
    """Unknown or unmapped status code from the API."""

    @classmethod
    def _missing_(cls, value: object) -> Any:  # noqa: ARG003
        """Return UNKNOWN for unmapped status codes."""
        return cls.UNKNOWN


class StoveState(StrEnum):
    """Simplified stove state derived from the raw status code.

    Mirrors the state machine in the Fumis mobile app. Maps the 14 raw
    StoveStatus codes into consumer-friendly states.
    """

    OFF = "off"
    """Stove is off (idle, post-cold-start, or post-wood-burning)."""

    HEATING_UP = "heating_up"
    """Stove is warming up before ignition."""

    IGNITION = "ignition"
    """Igniter is active or fire is catching."""

    BURNING = "burning"
    """Stove is actively burning (pellet or wood combustion)."""

    ECO = "eco"
    """Eco mode, maintaining temperature at reduced output."""

    COOLING = "cooling"
    """Stove is cooling down after being turned off."""

    UNKNOWN = "unknown"
    """Unknown or unmapped status."""


#: Maps each raw StoveStatus to a simplified StoveState.
_STATUS_TO_STATE: dict[StoveStatus, StoveState] = {
    StoveStatus.OFF: StoveState.OFF,
    StoveStatus.COLD_START_OFF: StoveState.OFF,
    StoveStatus.WOOD_BURNING_OFF: StoveState.OFF,
    StoveStatus.PRE_HEATING: StoveState.HEATING_UP,
    StoveStatus.IGNITION: StoveState.IGNITION,
    StoveStatus.PRE_COMBUSTION: StoveState.IGNITION,
    StoveStatus.COMBUSTION: StoveState.BURNING,
    StoveStatus.ECO: StoveState.ECO,
    StoveStatus.COOLING: StoveState.COOLING,
    StoveStatus.HYBRID_INIT: StoveState.HEATING_UP,
    StoveStatus.HYBRID_START: StoveState.IGNITION,
    StoveStatus.WOOD_START: StoveState.IGNITION,
    StoveStatus.COLD_START: StoveState.HEATING_UP,
    StoveStatus.WOOD_COMBUSTION: StoveState.BURNING,
    StoveStatus.UNKNOWN: StoveState.UNKNOWN,
}


@dataclass(frozen=True)
class StoveModelInfo:
    """Known stove model information."""

    manufacturer: str
    model: str


STOVE_MODELS: dict[tuple[int, int], StoveModelInfo] = {
    (2, 10): StoveModelInfo(manufacturer="Unknown", model="Pellet stove"),
    (2, 12): StoveModelInfo(manufacturer="Unknown", model="Hybrid stove"),
    (211, 15): StoveModelInfo(manufacturer="Austroflamm", model="Clou Duo"),
}
