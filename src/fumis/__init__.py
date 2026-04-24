"""Asynchronous Python client for the Fumis WiRCU API."""

from __future__ import annotations

from .const import StoveAlert, StoveError, StoveModelInfo, StoveState, StoveStatus
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
    FumisAntifreeze,
    FumisController,
    FumisDiagnostic,
    FumisDiagnosticItem,
    FumisEcoMode,
    FumisFan,
    FumisFuel,
    FumisHybrid,
    FumisInfo,
    FumisPower,
    FumisStatistic,
    FumisTemperature,
    FumisTimerProgram,
    FumisUnit,
    FumisWeekSchedule,
)

__all__ = [
    "Fumis",
    "FumisAntifreeze",
    "FumisAuthenticationError",
    "FumisConnectionError",
    "FumisConnectionTimeoutError",
    "FumisController",
    "FumisDiagnostic",
    "FumisDiagnosticItem",
    "FumisEcoMode",
    "FumisError",
    "FumisFan",
    "FumisFuel",
    "FumisHybrid",
    "FumisInfo",
    "FumisPower",
    "FumisResponseError",
    "FumisStatistic",
    "FumisStoveOfflineError",
    "FumisTemperature",
    "FumisTimerProgram",
    "FumisUnit",
    "FumisWeekSchedule",
    "StoveAlert",
    "StoveError",
    "StoveModelInfo",
    "StoveState",
    "StoveStatus",
]
