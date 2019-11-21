"""Tests for retreiving information from the Fumis WiRCU device."""
import aiohttp
import pytest
from fumis import Fumis
from fumis.exceptions import FumisError

from . import load_fixture


@pytest.mark.asyncio
async def test_info_update(event_loop, aresponses):
    """Test getting Fumis WiRCU device information and states."""
    aresponses.add(
        "api.fumis.si",
        "/v1/status",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("info.json"),
        ),
    )
    async with aiohttp.ClientSession(loop=event_loop) as session:
        fumis = Fumis(
            mac="AABBCCDDEEFF", password="1234", session=session, loop=event_loop,
        )
        info = await fumis.update_info()
        assert info
        assert info.unit_id == "AABBCCDDEEFF"
        assert info.unit_version == "2.0.0"
        assert info.controller_version == "1.7.0"
        assert info.ip == "192.168.1.2"
        assert info.rssi == -48
        assert info.signal_strength == 100
        assert info.state == "off"
        assert info.state_id == 1
        assert info.status == "off"
        assert info.status_id == 0
        assert info.temperature == 19.9
        assert info.target_temperature == 21.8
        assert info.heating_time == 1823340
        assert info.igniter_starts == 392
        assert info.misfires == 0
        assert info.overheatings == 0
        assert info.uptime == 58184580


@pytest.mark.asyncio
async def test_signal_strength(event_loop, aresponses):
    """Test retreiving Fumis WiRCU device WiFi signal strength."""
    aresponses.add(
        "api.fumis.si",
        "/v1/status",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"unit": {"rssi": -60}}',
        ),
    )

    async with aiohttp.ClientSession(loop=event_loop) as session:
        fumis = Fumis(
            mac="AABBCCDDEEFF", password="1234", session=session, loop=event_loop,
        )
        info = await fumis.update_info()
        assert info
        assert info.rssi == -60
        assert info.signal_strength == 80


@pytest.mark.asyncio
async def test_signal_strength_0(event_loop, aresponses):
    """Test retreiving Fumis WiRCU device WiFi signal strength with -100 dB."""
    aresponses.add(
        "api.fumis.si",
        "/v1/status",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text='{"unit": {"rssi": -100}}',
        ),
    )

    async with aiohttp.ClientSession(loop=event_loop) as session:
        fumis = Fumis(
            mac="AABBCCDDEEFF", password="1234", session=session, loop=event_loop,
        )
        info = await fumis.update_info()
        assert info
        assert info.rssi == -100
        assert info.signal_strength == 0


@pytest.mark.asyncio
async def test_info_none(event_loop, aresponses):
    """Test info data is None when communication has occured."""
    # Handle to run asserts on request in
    aresponses.add(
        "api.fumis.si",
        "/v1/status",
        "GET",
        aresponses.Response(
            status=500,
            headers={"Content-Type": "application/json"},
            text="Invalid response",
        ),
    )
    aresponses.add(
        "api.fumis.si",
        "/v1/status",
        "GET",
        aresponses.Response(
            status=200, headers={"Content-Type": "application/json"}, text="",
        ),
    )

    async with aiohttp.ClientSession(loop=event_loop) as session:
        fumis = Fumis(
            mac="AABBCCDDEEFF", password="1234", session=session, loop=event_loop,
        )
        with pytest.raises(FumisError):
            await fumis.update_info()
        assert fumis.info is None

        with pytest.raises(FumisError):
            await fumis.update_info()
        assert fumis.info is None
