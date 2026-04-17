"""Asynchronous Python client for the Fumis WiRCU API."""

from __future__ import annotations

from .const import StoveModelInfo, StoveStatus
from .exceptions import (
    FumisAuthenticationError,
    FumisConnectionError,
    FumisConnectionTimeoutError,
    FumisError,
    FumisResponseError,
    FumisStoveOfflineError,
)
from .fumis import Fumis
from .models import (
    Antifreeze,
    Controller,
    Diagnostic,
    DiagnosticItem,
    EcoMode,
    Fan,
    Fuel,
    Hybrid,
    Info,
    Power,
    Statistic,
    Temperature,
    TimerProgram,
    Unit,
    WeekSchedule,
)

__all__ = [
    "Antifreeze",
    "Controller",
    "Diagnostic",
    "DiagnosticItem",
    "EcoMode",
    "Fan",
    "Fuel",
    "Fumis",
    "FumisAuthenticationError",
    "FumisConnectionError",
    "FumisConnectionTimeoutError",
    "FumisError",
    "FumisResponseError",
    "FumisStoveOfflineError",
    "Hybrid",
    "Info",
    "Power",
    "Statistic",
    "StoveModelInfo",
    "StoveStatus",
    "Temperature",
    "TimerProgram",
    "Unit",
    "WeekSchedule",
]
