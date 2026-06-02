"""Common fixtures and helpers for Fumis WiRCU tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import aiohttp
import pytest
from aioresponses import aioresponses
from aioresponses import core as aioresponses_core

from fumis import Fumis

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

AIOHTTP_REQUIRES_STREAM_WRITER = (
    "stream_writer" in aiohttp.ClientResponse.__init__.__code__.co_varnames
)


class AIOHTTPStreamWriter:
    """Minimal aiohttp stream writer for tests.

    aiohttp 3.14 reads only ``output_size`` during ClientResponse initialization
    for this mocked response path.
    """

    output_size = 0


class AioresponsesClientResponse(aioresponses_core.ClientResponse):
    """Backwards-compatible ClientResponse for aioresponses."""

    def __init__(self, *args, **kwargs):
        """Initialize and provide a stream_writer for aiohttp 3.14+."""
        kwargs.setdefault("stream_writer", AIOHTTPStreamWriter())
        super().__init__(*args, **kwargs)


@pytest.fixture(scope="session", autouse=True)
def setup_aioresponses_aiohttp_compat() -> Generator[None, None, None]:
    """Patch aioresponses ClientResponse for aiohttp compatibility in tests."""
    if not AIOHTTP_REQUIRES_STREAM_WRITER:
        yield
        return

    original_client_response = aioresponses_core.ClientResponse
    aioresponses_core.ClientResponse = AioresponsesClientResponse
    yield
    aioresponses_core.ClientResponse = original_client_response

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
