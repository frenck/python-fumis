"""Models for the Fumis WiRCU API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from awesomeversion import AwesomeVersion
from mashumaro import field_options
from mashumaro.config import BaseConfig
from mashumaro.mixins.orjson import DataClassORJSONMixin
from mashumaro.types import SerializationStrategy

from .const import STOVE_MODELS, StoveModelInfo, StoveStatus


class _AwesomeVersionStrategy(SerializationStrategy):
    """Serialize AwesomeVersion to/from string for mashumaro."""

    def serialize(self, value: AwesomeVersion) -> str:
        """Serialize to string."""
        return str(value)

    def deserialize(self, value: str) -> AwesomeVersion:
        """Deserialize from string."""
        return AwesomeVersion(value)


class _StringToIntStrategy(SerializationStrategy):
    """Deserialize a string-encoded integer (e.g., RSSI "-48")."""

    def serialize(self, value: int) -> str:
        """Serialize to string."""
        return str(value)

    def deserialize(self, value: str | int) -> int:
        """Deserialize from string or int."""
        return int(value)


class _StringToFloatStrategy(SerializationStrategy):
    """Deserialize a string-encoded float (e.g., heatingSlope "0.0")."""

    def serialize(self, value: float) -> float:
        """Serialize to float."""
        return value

    def deserialize(self, value: str | float) -> float:
        """Deserialize from string, float, or int."""
        return float(value)


class _TimestampStrategy(SerializationStrategy):
    """Convert a unix timestamp to a UTC datetime."""

    def serialize(self, value: datetime) -> int:
        """Serialize to unix timestamp."""
        return int(value.timestamp())

    def deserialize(self, value: int) -> datetime:
        """Deserialize from unix timestamp."""
        return datetime.fromtimestamp(value, tz=UTC)


class _OptionalTimestampStrategy(SerializationStrategy):
    """Convert a unix timestamp to a UTC datetime, with -1 as None."""

    def serialize(self, value: datetime | None) -> int:
        """Serialize to unix timestamp, None becomes -1."""
        return -1 if value is None else int(value.timestamp())

    def deserialize(self, value: int) -> datetime | None:
        """Deserialize from unix timestamp, -1 becomes None."""
        return None if value == -1 else datetime.fromtimestamp(value, tz=UTC)


class _TimedeltaSecondsStrategy(SerializationStrategy):
    """Convert seconds to a timedelta."""

    def serialize(self, value: timedelta) -> int:
        """Serialize to seconds."""
        return int(value.total_seconds())

    def deserialize(self, value: int | str) -> timedelta:
        """Deserialize from seconds (may be string-encoded)."""
        return timedelta(seconds=int(value))


class _BaseModel(DataClassORJSONMixin):
    """Base model for all Fumis models."""

    # pylint: disable-next=too-few-public-methods
    class Config(BaseConfig):
        """Mashumaro configuration."""

        omit_none = True
        serialization_strategy = {  # noqa: RUF012
            AwesomeVersion: _AwesomeVersionStrategy(),
        }


@dataclass(frozen=True)
class DiagnosticItem(_BaseModel):
    """A single diagnostic variable or parameter entry."""

    id: int
    value: int = 0


@dataclass(frozen=True)
class Diagnostic(_BaseModel):
    """Diagnostic data from the Fumis controller."""

    variables: list[DiagnosticItem] = field(default_factory=list)
    parameters: list[DiagnosticItem] = field(default_factory=list)
    timers: list[DiagnosticItem] = field(default_factory=list)

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
class Temperature(_BaseModel):
    """A temperature channel from the Fumis controller."""

    id: int
    actual: float = 0
    setpoint: float = field(default=0, metadata=field_options(alias="set"))
    on_main_screen: bool = field(
        default=False, metadata=field_options(alias="onMainScreen")
    )
    actual_type: int = field(default=0, metadata=field_options(alias="actualType"))
    set_type: int = field(default=0, metadata=field_options(alias="setType"))
    name: str | None = None
    weight: int = 0


@dataclass(frozen=True)
class Power(_BaseModel):
    """Power state of the Fumis controller."""

    kw: float = 0
    actual_power: int = field(default=0, metadata=field_options(alias="actualPower"))
    set_power: int = field(default=0, metadata=field_options(alias="setPower"))
    set_type: int = field(default=0, metadata=field_options(alias="setType"))
    actual_type: int = field(default=0, metadata=field_options(alias="actualType"))


@dataclass(frozen=True)
class Fan(_BaseModel):
    """A fan entry from the Fumis controller."""

    id: int
    speed: int = 0
    speed_type: int = field(default=0, metadata=field_options(alias="speedType"))
    weight: int = 0


@dataclass(frozen=True)
class Fuel(_BaseModel):
    """A fuel entry from the Fumis controller."""

    id: int
    quality: int = 0
    quality_type: int = field(default=0, metadata=field_options(alias="qualityType"))
    quality_actual: int | None = field(
        default=None, metadata=field_options(alias="qualityActual")
    )
    quantity: float | None = None
    quantity_display: int | None = field(
        default=None, metadata=field_options(alias="quantityDisplay")
    )
    quantity_set_type: int = field(
        default=0, metadata=field_options(alias="quantitySetType")
    )
    quantity_actual_type: int = field(
        default=0, metadata=field_options(alias="quantityActualType")
    )
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
class EcoMode(_BaseModel):
    """Eco mode state of the Fumis controller."""

    eco_mode_enable: int | None = field(
        default=None, metadata=field_options(alias="ecoModeEnable")
    )
    eco_mode_set_type: int | None = field(
        default=None, metadata=field_options(alias="ecoModeSetType")
    )

    @property
    def enabled(self) -> bool:
        """Return whether eco mode is enabled."""
        return self.eco_mode_enable == 1


@dataclass(frozen=True)
class Hybrid(_BaseModel):
    """Hybrid mode state (wood + pellet stoves)."""

    actual_type: int = field(default=0, metadata=field_options(alias="actualType"))
    operation: int = 0
    state: int = 0


@dataclass(frozen=True)
class Antifreeze(_BaseModel):
    """Antifreeze protection settings."""

    temperature: float | None = None
    enable: bool | None = None


@dataclass(frozen=True)
class Statistic(_BaseModel):
    """Statistics counters from the Fumis controller."""

    igniter_starts: int = field(
        default=0, metadata=field_options(alias="igniterStarts")
    )
    uptime: timedelta = field(
        default_factory=lambda: timedelta(0),
        metadata=field_options(
            serialization_strategy=_TimedeltaSecondsStrategy(),
        ),
    )
    heating_time: timedelta = field(
        default_factory=lambda: timedelta(0),
        metadata=field_options(
            alias="heatingTime",
            serialization_strategy=_TimedeltaSecondsStrategy(),
        ),
    )
    service_time: timedelta = field(
        default_factory=lambda: timedelta(0),
        metadata=field_options(
            alias="serviceTime",
            serialization_strategy=_TimedeltaSecondsStrategy(),
        ),
    )
    overheatings: int = 0
    misfires: int = 0
    fuel_quantity_used: int = field(
        default=0, metadata=field_options(alias="fuelQuantityUsed")
    )


@dataclass(frozen=True)
class Unit(_BaseModel):
    """WiRCU box information."""

    id: str = "Unknown"
    type: int = 0
    version: AwesomeVersion = field(default_factory=lambda: AwesomeVersion("0"))
    command: int | None = None
    rssi: int = field(
        default=-100,
        metadata=field_options(
            serialization_strategy=_StringToIntStrategy(),
        ),
    )
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
class TimerProgram:
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
class WeekSchedule:
    """Weekly timer schedule parsed from diagnostic timers."""

    programs: tuple[TimerProgram, TimerProgram, TimerProgram, TimerProgram]
    """The 4 available timer programs (time slots)."""

    days: dict[str, tuple[bool, bool]]
    """Day-of-week enables: day name -> (slot 1 enabled, slot 2 enabled)."""

    @property
    def active_days(self) -> list[str]:
        """Return list of day names that have at least one slot enabled."""
        return [day for day, (s1, s2) in self.days.items() if s1 or s2]


@dataclass(frozen=True)
# pylint: disable-next=too-many-instance-attributes
class Controller(_BaseModel):
    """Fumis stove controller state."""

    type: int = 0
    version: AwesomeVersion = field(default_factory=lambda: AwesomeVersion("0"))
    command: int = -1
    status: int = -1
    error: int = 0
    alert: int = 0
    heating_slope: float = field(
        default=0,
        metadata=field_options(
            alias="heatingSlope",
            serialization_strategy=_StringToFloatStrategy(),
        ),
    )
    current_time: datetime = field(
        default_factory=lambda: datetime.fromtimestamp(0, tz=UTC),
        metadata=field_options(
            alias="currentTime",
            serialization_strategy=_TimestampStrategy(),
        ),
    )
    timer_enable: bool = field(
        default=False, metadata=field_options(alias="timerEnable")
    )
    fuel_type: int = field(default=0, metadata=field_options(alias="fuelType"))
    time_to_service: int = field(
        default=0, metadata=field_options(alias="timeToService")
    )
    delayed_start_at: datetime | None = field(
        default=None,
        metadata=field_options(
            alias="delayedStartAt",
            serialization_strategy=_OptionalTimestampStrategy(),
        ),
    )
    delayed_stop_at: datetime | None = field(
        default=None,
        metadata=field_options(
            alias="delayedStopAt",
            serialization_strategy=_OptionalTimestampStrategy(),
        ),
    )

    power: Power = field(default_factory=Power)
    statistic: Statistic = field(default_factory=Statistic)
    diagnostic: Diagnostic = field(default_factory=Diagnostic)
    eco_mode: EcoMode | None = field(
        default=None, metadata=field_options(alias="ecoMode")
    )
    hybrid: Hybrid | None = None
    antifreeze: Antifreeze | None = None
    fans: list[Fan] = field(default_factory=list)
    temperatures: list[Temperature] = field(default_factory=list)
    fuels: list[Fuel] = field(default_factory=list)

    # -- Status --

    @property
    def stove_status(self) -> StoveStatus:
        """Return the stove operational status as an enum."""
        return StoveStatus(self.status)

    @property
    def on(self) -> bool:
        """Return whether the stove is commanded on."""
        return self.command == 2

    # -- Temperatures --

    @property
    def main_temperature(self) -> Temperature | None:
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

    # -- Diagnostic sensors --

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

    @property
    def backwater_temperature(self) -> int | None:
        """Return backwater temperature (for hydronic stoves).

        From VARIABLE_BACKWATER_TEMPERATURE (var[22]).
        Returns None if not available.
        """
        return self.diagnostic.variable(22)

    # -- Schedule --

    @property
    def schedule(self) -> WeekSchedule:
        """Parse the weekly timer schedule from diagnostic timers."""
        t = self.diagnostic.timer
        programs = (
            TimerProgram(t(0), t(1), t(2), t(3)),
            TimerProgram(t(4), t(5), t(6), t(7)),
            TimerProgram(t(8), t(9), t(10), t(11)),
            TimerProgram(t(12), t(13), t(14), t(15)),
        )
        days = {
            day: (t(16 + i * 2) == 1, t(17 + i * 2) == 1) for i, day in enumerate(_DAYS)
        }
        return WeekSchedule(programs=programs, days=days)

    # -- Lookups --

    def fan(self, fan_id: int = 1) -> Fan | None:
        """Find a fan entry by ID."""
        return next((f for f in self.fans if f.id == fan_id), None)

    def fuel(self, fuel_id: int = 1) -> Fuel | None:
        """Find a fuel entry by ID."""
        return next((f for f in self.fuels if f.id == fuel_id), None)

    def temperature_channel(self, channel_id: int) -> Temperature | None:
        """Find a temperature channel by ID."""
        return next((t for t in self.temperatures if t.id == channel_id), None)


@dataclass(frozen=True)
class Info(_BaseModel):
    """Top-level Fumis WiRCU API response.

    This is the complete device status returned by GET /v1/status.
    All structured data is accessible via the nested `unit` and
    `controller` objects.
    """

    unit: Unit = field(default_factory=Unit)
    controller: Controller = field(default_factory=Controller)
    api_version: AwesomeVersion = field(
        default_factory=lambda: AwesomeVersion("0"),
        metadata=field_options(alias="apiVersion"),
    )
