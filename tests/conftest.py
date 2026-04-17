"""Common fixtures and helpers for Fumis WiRCU tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import aiohttp
import pytest
from aioresponses import aioresponses

from fumis import Fumis

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    """Load a fixture file by name."""
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


@pytest.fixture
def responses() -> Generator[aioresponses, None, None]:
    """Yield an aioresponses instance that patches aiohttp client sessions."""
    with aioresponses() as mocker:
        yield mocker


@pytest.fixture
async def fumis() -> AsyncGenerator[Fumis, None]:
    """Yield a Fumis client wired with default settings."""
    async with aiohttp.ClientSession() as session:
        yield Fumis(mac="AABBCCDDEEFF", password="1234", session=session)
