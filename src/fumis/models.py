"""Models for the Fumis WiRCU API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Annotated

from awesomeversion import AwesomeVersion
from probatio import (
    REMOVE_EXTRA,
    AsTimedelta,
    Coerce,
    FromEpoch,
    Key,
    Maybe,
    SchemaMixin,
)

from .const import (
    STOVE_MODELS,
    StoveAlert,
    StoveError,
    StoveModelInfo,
    StoveState,
    StoveStatus,
)


def _sentinel_int(value: str | int) -> int | None:
    """Map the -1 sentinel to None, otherwise coerce to int."""
    result = int(value)
    return None if result == -1 else result


def _sentinel_epoch(value: int) -> datetime | None:
    """Map the -1 sentinel to None, otherwise a unix timestamp to a UTC datetime."""
    seconds = int(value)
    return None if seconds == -1 else datetime.fromtimestamp(seconds, tz=UTC)


@dataclass(frozen=True)
class FumisDiagnosticItem:
    """A single diagnostic variable or parameter entry."""

    id: int
    value: int = 0


@dataclass(frozen=True)
class FumisDiagnostic:
    """FumisDiagnostic data from the Fumis controller."""

    variables: list[FumisDiagnosticItem] = field(default_factory=list)
    parameters: list[FumisDiagnosticItem] = field(default_factory=list)
    timers: list[FumisDiagnosticItem] = field(default_factory=list)

    def variable(self, variable_id: int) -> int | None:
        """Get the value of a diagnostic variable by ID.

        Returns None if the variable is not present in the response.
        """
        return next(
            (v.value for v in self.variables if v.id == variable_id),
            None,
        )

    def parameter(self, parameter_id: int) -> int | None:
        """Get the value of a diagnostic parameter by ID.

        Returns None if the parameter is not present in the response.
        """
        return next(
            (p.value for p in self.parameters if p.id == parameter_id),
            None,
        )

    def timer(self, timer_id: int) -> int:
        """Get the value of a diagnostic timer by ID.

        Returns 0 if the timer is not present in the response.
        """
        return next(
            (t.value for t in self.timers if t.id == timer_id),
            0,
        )


@dataclass(frozen=True)
class FumisTemperature:
    """A temperature channel from the Fumis controller."""

    id: int
    actual: float = 0
    setpoint: Annotated[float, Key(alias="set")] = 0
    on_main_screen: Annotated[bool, Key(alias="onMainScreen")] = False
    actual_type: Annotated[int, Key(alias="actualType")] = 0
    set_type: Annotated[int, Key(alias="setType")] = 0
    name: str | None = None
    weight: int = 0


@dataclass(frozen=True)
class FumisPower:
    """FumisPower state of the Fumis controller."""

    kw: Annotated[float, Coerce(float)] = 0
    actual_power: Annotated[int, Key(alias="actualPower")] = 0
    set_power: Annotated[int, Key(alias="setPower")] = 0
    set_type: Annotated[int, Key(alias="setType")] = 0
    actual_type: Annotated[int, Key(alias="actualType")] = 0


@dataclass(frozen=True)
class FumisFan:
    """A fan entry from the Fumis controller."""

    id: int
    speed: int = 0
    speed_type: Annotated[int, Key(alias="speedType")] = 0
    weight: int = 0


@dataclass(frozen=True)
class FumisFuel:
    """A fuel entry from the Fumis controller."""

    id: int
    quality: int = 0
    quality_type: Annotated[int, Key(alias="qualityType")] = 0
    quality_actual: Annotated[int | None, Key(alias="qualityActual")] = None
    quantity: float | None = None
    quantity_display: Annotated[int | None, Key(alias="quantityDisplay")] = None
    quantity_set_type: Annotated[int, Key(alias="quantitySetType")] = 0
    quantity_actual_type: Annotated[int, Key(alias="quantityActualType")] = 0
    name: str | None = None

    @property
    def quantity_percentage(self) -> float | None:
        """Return fuel quantity as a percentage (0-100).

        Returns None if the stove does not report fuel quantity.
        """
        if self.quantity is None:
            return None
        return self.quantity * 100


@dataclass(frozen=True)
class FumisEcoMode:
    """Eco mode state of the Fumis controller."""

    eco_mode_enable: Annotated[int | None, Key(alias="ecoModeEnable")] = None
    eco_mode_set_type: Annotated[int | None, Key(alias="ecoModeSetType")] = None

    @property
    def enabled(self) -> bool:
        """Return whether eco mode is enabled."""
        return self.eco_mode_enable == 1


@dataclass(frozen=True)
class FumisHybrid:
    """FumisHybrid mode state (wood + pellet stoves)."""

    actual_type: Annotated[int, Key(alias="actualType")] = 0
    operation: int = 0
    state: int = 0


@dataclass(frozen=True)
class FumisAntifreeze:
    """FumisAntifreeze protection settings."""

    temperature: float | None = None
    enable: bool | None = None


@dataclass(frozen=True)
class FumisStatistic:
    """Statistics counters from the Fumis controller."""

    igniter_starts: Annotated[int, Key(alias="igniterStarts")] = 0
    uptime: Annotated[timedelta, AsTimedelta()] = field(
        default_factory=lambda: timedelta(0)
    )
    heating_time: Annotated[timedelta, Key(alias="heatingTime"), AsTimedelta()] = field(
        default_factory=lambda: timedelta(0)
    )
    service_time: Annotated[timedelta, Key(alias="serviceTime"), AsTimedelta()] = field(
        default_factory=lambda: timedelta(0)
    )
    overheatings: int = 0
    misfires: int = 0
    fuel_quantity_used: Annotated[int, Key(alias="fuelQuantityUsed")] = 0


@dataclass(frozen=True)
class FumisUnit:
    """WiRCU box information."""

    id: str = "Unknown"
    type: int = 0
    version: Annotated[AwesomeVersion, Coerce(AwesomeVersion)] = field(
        default_factory=lambda: AwesomeVersion("0")
    )
    command: int | None = None
    rssi: Annotated[int, Coerce(int)] = -100
    ip: str = "Unknown"
    timezone: str | None = None
    temperature: float | None = None

    @property
    def signal_strength(self) -> int:
        """Convert RSSI to signal strength percentage (0-100)."""
        if self.rssi <= -100:
            return 0
        if self.rssi >= -50:
            return 100
        return 2 * (self.rssi + 100)


_DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


@dataclass(frozen=True)
class FumisTimerProgram:
    """A single timer program (time slot) from the weekly schedule."""

    start_hour: int
    start_minute: int
    stop_hour: int
    stop_minute: int

    @property
    def active(self) -> bool:
        """Return whether this program has a schedule set."""
        return (
            self.start_hour != 0
            or self.start_minute != 0
            or self.stop_hour != 0
            or self.stop_minute != 0
        )

    def __str__(self) -> str:
        """Format as HH:MM-HH:MM."""
        return (
            f"{self.start_hour:02d}:{self.start_minute:02d}"
            f"-{self.stop_hour:02d}:{self.stop_minute:02d}"
        )


@dataclass(frozen=True)
class FumisWeekSchedule:
    """Weekly timer schedule parsed from diagnostic timers."""

    programs: tuple[
        FumisTimerProgram,
        FumisTimerProgram,
        FumisTimerProgram,
        FumisTimerProgram,
    ]
    """The 4 available timer programs (time slots)."""

    days: dict[str, tuple[bool, bool]]
    """Day-of-week enables: day name -> (slot 1 enabled, slot 2 enabled)."""

    @property
    def active_days(self) -> list[str]:
        """Return list of day names that have at least one slot enabled."""
        return [day for day, (s1, s2) in self.days.items() if s1 or s2]


@dataclass(frozen=True)
# pylint: disable-next=too-many-instance-attributes,too-many-public-methods
class FumisController:
    """Fumis stove controller state."""

    type: int = 0
    version: Annotated[AwesomeVersion, Coerce(AwesomeVersion)] = field(
        default_factory=lambda: AwesomeVersion("0")
    )
    command: int = -1
    status: int = -1
    error: int = 0
    alert: int = 0
    heating_slope: Annotated[float, Key(alias="heatingSlope"), Coerce(float)] = 0
    current_time: Annotated[datetime, Key(alias="currentTime"), FromEpoch()] = field(
        default_factory=lambda: datetime.fromtimestamp(0, tz=UTC)
    )
    timer_enable: Annotated[bool, Key(alias="timerEnable")] = False
    fuel_type: Annotated[int, Key(alias="fuelType")] = 0
    time_to_service: Annotated[
        int | None, Key(alias="timeToService"), Maybe(Coerce(_sentinel_int))
    ] = None
    delayed_start_at: Annotated[
        datetime | None, Key(alias="delayedStartAt"), Maybe(Coerce(_sentinel_epoch))
    ] = None
    delayed_stop_at: Annotated[
        datetime | None, Key(alias="delayedStopAt"), Maybe(Coerce(_sentinel_epoch))
    ] = None

    power: FumisPower = field(default_factory=FumisPower)
    statistic: FumisStatistic = field(default_factory=FumisStatistic)
    diagnostic: FumisDiagnostic = field(default_factory=FumisDiagnostic)
    eco_mode: Annotated[FumisEcoMode | None, Key(alias="ecoMode")] = None
    hybrid: FumisHybrid | None = None
    antifreeze: FumisAntifreeze | None = None
    fans: list[FumisFan] = field(default_factory=list)
    temperatures: list[FumisTemperature] = field(default_factory=list)
    fuels: list[FumisFuel] = field(default_factory=list)

    # -- Status --

    @property
    def stove_status(self) -> StoveStatus:
        """Return the stove operational status as an enum."""
        return StoveStatus(self.status)

    @property
    def stove_error(self) -> StoveError:
        """Return the stove error as an enum.

        Converts the raw integer error code to a StoveError enum
        whose value matches the device display (e.g., E102).
        """
        return StoveError.from_code(self.error)

    @property
    def stove_alert(self) -> StoveAlert:
        """Return the stove alert as an enum.

        Converts the raw integer alert code to a StoveAlert enum
        whose value matches the device display (e.g., A004).
        """
        return StoveAlert.from_code(self.alert)

    @property
    def on(self) -> bool:
        """Return whether the stove is operationally active.

        Based on status, not command. The command field is transient
        and resets after being acknowledged by the controller.
        """
        return self.stove_status not in (
            StoveStatus.OFF,
            StoveStatus.COLD_START_OFF,
            StoveStatus.WOOD_BURNING_OFF,
            StoveStatus.UNKNOWN,
        )

    @property
    def state(self) -> StoveState:
        """Return the simplified stove state.

        Maps the 14 raw status codes into consumer-friendly states
        (off, heating_up, ignition, burning, eco, cooling, unknown).
        """
        return StoveState.from_status(self.stove_status)

    # -- Temperatures --

    @property
    def main_temperature(self) -> FumisTemperature | None:
        """Find the primary temperature channel.

        Prefers the entry marked as on-screen with an actual reading;
        falls back to the first entry if none qualifies.
        """
        for temp in self.temperatures:
            if temp.on_main_screen and temp.actual_type > 0:
                return temp
        return self.temperatures[0] if self.temperatures else None

    @property
    def combustion_chamber_temperature(self) -> float | None:
        """Return the combustion chamber temperature.

        Looks for temperature channel id=7 (TEMPERATURE_COMBUSTION_CHAMBER
        from the Fumis app). Returns None if not available.
        """
        for temp in self.temperatures:
            if temp.id == 7:
                return temp.actual
        return None

    # -- FumisDiagnostic sensors --

    @property
    def exhaust_temperature(self) -> int | None:
        """Return the exhaust/flue gas temperature.

        From VARIABLE_GASSES_TEMPERATURE (var[11]).
        Returns None if not available.
        """
        return self.diagnostic.variable(11)

    @property
    def fan1_speed(self) -> int | None:
        """Return fan 1 speed.

        From VARIABLE_FAN_1_SPEED (var[4]).
        Returns None if not available.
        """
        return self.diagnostic.variable(4)

    @property
    def fan2_speed(self) -> int | None:
        """Return fan 2 speed.

        From VARIABLE_FAN_2_SPEED (var[12]).
        Returns None if not available.
        """
        return self.diagnostic.variable(12)

    @property
    def door_open(self) -> bool | None:
        """Return whether the combustion door is open.

        From VARIABLE_I04 (var[33]). Confirmed by physical testing
        on Austroflamm Clou Duo.
        Returns True if open, False if closed, None if not available.
        """
        value = self.diagnostic.variable(33)
        if value is None:
            return None
        return value == 0

    @property
    def f02(self) -> int | None:
        """Return F02 sensor input.

        From VARIABLE_F02 (var[34]).
        Returns None if not available.
        """
        return self.diagnostic.variable(34)

    @property
    def pressure(self) -> int | None:
        """Return pressure sensor value.

        From VARIABLE_PRESSURE (var[35]).
        Returns None if not available.
        """
        return self.diagnostic.variable(35)

    # -- Model identification --

    @property
    def stove_model(self) -> int | None:
        """Return the stove model identifier.

        From VARIABLE_STOVE_MODEL (var[96]).
        Returns None if not available.
        """
        return self.diagnostic.variable(96)

    @property
    def parameter_version(self) -> int | None:
        """Return the parameter version.

        From VARIABLE_PARAMETER_VERSION (var[97]).
        Returns None if not available.
        """
        return self.diagnostic.variable(97)

    @property
    def model_info(self) -> StoveModelInfo | None:
        """Return known stove model information.

        Looks up the combination of stove_model (var[96]) and
        parameter_version (var[97]) in the known models database.
        Returns None if the model is unknown.
        """
        model = self.stove_model
        version = self.parameter_version
        if model is None or version is None:
            return None
        return STOVE_MODELS.get((model, version))

    @property
    def manufacturer(self) -> str | None:
        """Return the stove manufacturer name, if known."""
        info = self.model_info
        return info.manufacturer if info else None

    @property
    def model_name(self) -> str | None:
        """Return the stove model name, if known."""
        info = self.model_info
        return info.model if info else None

    # -- Schedule --

    @property
    def schedule(self) -> FumisWeekSchedule:
        """Parse the weekly timer schedule from diagnostic timers."""
        t = self.diagnostic.timer
        programs = (
            FumisTimerProgram(t(0), t(1), t(2), t(3)),
            FumisTimerProgram(t(4), t(5), t(6), t(7)),
            FumisTimerProgram(t(8), t(9), t(10), t(11)),
            FumisTimerProgram(t(12), t(13), t(14), t(15)),
        )
        days = {
            day: (t(16 + i * 2) == 1, t(17 + i * 2) == 1) for i, day in enumerate(_DAYS)
        }
        return FumisWeekSchedule(programs=programs, days=days)

    # -- Lookups --

    def fan(self, fan_id: int = 1) -> FumisFan | None:
        """Find a fan entry by ID."""
        return next((f for f in self.fans if f.id == fan_id), None)

    def fuel(self, fuel_id: int = 1) -> FumisFuel | None:
        """Find a fuel entry by ID."""
        return next((f for f in self.fuels if f.id == fuel_id), None)

    def temperature_channel(self, channel_id: int) -> FumisTemperature | None:
        """Find a temperature channel by ID."""
        return next((t for t in self.temperatures if t.id == channel_id), None)


@dataclass(frozen=True)
class FumisInfo(SchemaMixin, extra=REMOVE_EXTRA):
    """Top-level Fumis WiRCU API response.

    This is the complete device status returned by GET /v1/status.
    All structured data is accessible via the nested `unit` and
    `controller` objects. Parse a raw API payload with `FumisInfo.from_dict`,
    which validates and constructs the whole tree, dropping unmodeled keys.
    """

    unit: FumisUnit = field(default_factory=FumisUnit)
    controller: FumisController = field(default_factory=FumisController)
    api_version: Annotated[
        AwesomeVersion, Key(alias="apiVersion"), Coerce(AwesomeVersion)
    ] = field(default_factory=lambda: AwesomeVersion("0"))
