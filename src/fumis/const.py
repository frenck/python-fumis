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

    @classmethod
    def from_status(cls, status: StoveStatus) -> StoveState:
        """Convert a raw StoveStatus to a simplified StoveState."""
        return _STATUS_TO_STATE.get(status, cls.UNKNOWN)


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


class StoveError(StrEnum):
    """Stove error code (from controller.error).

    Values match the display format on the device (e.g., E102).
    Use `StoveError.from_code()` to convert the raw integer from the API.
    """

    IGNITION_FAILED = "E101"
    """Ignition failed, water overtemperature, or backfire protection."""

    CHIMNEY_DIRTY = "E102"
    """Chimney/burning pot dirty, or manually stopped before flame detection."""

    SENSOR_T02 = "E105"
    """Sensor T02 malfunction or disconnected."""

    SENSOR_T03_T05 = "E106"
    """Sensor T03 or T05 malfunction or disconnected."""

    SENSOR_T04 = "E107"
    """Sensor T04 malfunction or disconnected."""

    SAFETY_SWITCH = "E108"
    """Security switch I01 tripped (STB). Reset and restart."""

    PRESSURE_SENSOR_OFF = "E109"
    """Pressure sensor switched OFF. Reset and restart."""

    SENSOR_T01_T02 = "E110"
    """Sensor T01 or T02 malfunction or disconnected."""

    SENSOR_T01_T03 = "E111"
    """Sensor T01 or T03 malfunction or disconnected."""

    FLUE_GAS_OVERTEMP = "E113"
    """Flue gases overtemperature. Clean chimney/heat exchanger."""

    FUEL_IGNITION_TIMEOUT = "E114"
    """Fuel ignition timeout (empty burning pot) or tank empty."""

    GENERAL_ERROR = "E115"
    """General error. Call service."""

    MFDOOR_ALARM = "E239"
    """MFDoor alarm."""

    FIRE_ERROR = "E240"
    """Fire error."""

    CHIMNEY_ALARM = "E241"
    """Chimney alarm."""

    GRATE_ERROR = "E243"
    """Grate error."""

    NTC2_ALARM = "E244"
    """NTC2 alarm."""

    NTC3_ALARM = "E245"
    """NTC3 alarm."""

    DOOR_ALARM = "E247"
    """Door alarm."""

    PRESSURE_ALARM = "E248"
    """Pressure alarm."""

    NTC1_ALARM = "E249"
    """NTC1 alarm."""

    TC1_ALARM = "E250"
    """TC1 alarm."""

    GAS_ALARM = "E252"
    """Gas alarm."""

    NO_PELLET_ALARM = "E253"
    """No pellet alarm."""

    UNKNOWN = "unknown"
    """Unknown or unmapped error code from the API."""

    @classmethod
    def from_code(cls, code: int) -> StoveError | None:
        """Convert a raw error code integer to a StoveError enum.

        Returns None when there is no active error (code 0).
        """
        if code == 0:
            return None
        formatted = f"E{code:03d}"
        try:
            return cls(formatted)
        except ValueError:
            return cls.UNKNOWN

    @property
    def description(self) -> str:
        """Return a human-readable description of this error."""
        if self is StoveError.UNKNOWN:
            return "Unknown error code"
        return _ERROR_DESCRIPTIONS.get(self, self.value)


class StoveAlert(StrEnum):
    """Stove alert/warning code (from controller.alert).

    Values match the display format on the device (e.g., A004).
    Use `StoveAlert.from_code()` to convert the raw integer from the API.
    """

    LOW_FUEL = "A001"
    """Low fuel level - refuel the tank."""

    SERVICE_DUE = "A002"
    """Service due - call for regular maintenance."""

    FLUE_GAS_WARNING = "A003"
    """Flue gas temperature warning - clean chimney/heat exchanger."""

    LOW_BATTERY = "A004"
    """Low battery - call service for replacement."""

    SPEED_SENSOR_FAILURE = "A005"
    """Speed sensor failure - call service."""

    DOOR_OPEN = "A006"
    """Door open - close the door."""

    AIRFLOW_MALFUNCTION = "A007"
    """Alternative operating mode, limited functionality (airflow sensor)."""

    UNKNOWN = "unknown"
    """Unknown or unmapped alert code from the API."""

    @classmethod
    def from_code(cls, code: int) -> StoveAlert | None:
        """Convert a raw alert code integer to a StoveAlert enum.

        Returns None when there is no active alert (code 0).
        """
        if code == 0:
            return None
        formatted = f"A{code:03d}"
        try:
            return cls(formatted)
        except ValueError:
            return cls.UNKNOWN

    @property
    def description(self) -> str:
        """Return a human-readable description of this alert."""
        if self is StoveAlert.UNKNOWN:
            return "Unknown alert code"
        return _ALERT_DESCRIPTIONS.get(self, self.value)


_ERROR_DESCRIPTIONS: dict[StoveError, str] = {
    StoveError.IGNITION_FAILED: (
        "Ignition failed / water overtemperature / backfire protection"
    ),
    StoveError.CHIMNEY_DIRTY: "Chimney/burning pot dirty or manually stopped",
    StoveError.SENSOR_T02: "Sensor T02 malfunction",
    StoveError.SENSOR_T03_T05: "Sensor T03/T05 malfunction",
    StoveError.SENSOR_T04: "Sensor T04 malfunction",
    StoveError.SAFETY_SWITCH: "Security switch I01 tripped (STB)",
    StoveError.PRESSURE_SENSOR_OFF: "Pressure sensor switched OFF",
    StoveError.SENSOR_T01_T02: "Sensor T01/T02 malfunction",
    StoveError.SENSOR_T01_T03: "Sensor T01/T03 malfunction",
    StoveError.FLUE_GAS_OVERTEMP: "Flue gas overtemperature",
    StoveError.FUEL_IGNITION_TIMEOUT: "Fuel ignition timeout / tank empty",
    StoveError.GENERAL_ERROR: "General error",
    StoveError.MFDOOR_ALARM: "MFDoor Alarm",
    StoveError.FIRE_ERROR: "Fire Error",
    StoveError.CHIMNEY_ALARM: "Chimney Alarm",
    StoveError.GRATE_ERROR: "Grate Error",
    StoveError.NTC2_ALARM: "NTC2 Alarm",
    StoveError.NTC3_ALARM: "NTC3 Alarm",
    StoveError.DOOR_ALARM: "Door Alarm",
    StoveError.PRESSURE_ALARM: "Pressure Alarm",
    StoveError.NTC1_ALARM: "NTC1 Alarm",
    StoveError.TC1_ALARM: "TC1 Alarm",
    StoveError.GAS_ALARM: "Gas Alarm",
    StoveError.NO_PELLET_ALARM: "No Pellet Alarm",
}

_ALERT_DESCRIPTIONS: dict[StoveAlert, str] = {
    StoveAlert.LOW_FUEL: "Low fuel level",
    StoveAlert.SERVICE_DUE: "Service due",
    StoveAlert.FLUE_GAS_WARNING: "Flue gas temperature warning",
    StoveAlert.LOW_BATTERY: "Low battery",
    StoveAlert.SPEED_SENSOR_FAILURE: "Speed sensor failure",
    StoveAlert.DOOR_OPEN: "Door open",
    StoveAlert.AIRFLOW_MALFUNCTION: "Airflow sensor malfunction (limited mode)",
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
