"""Tests for action performed against a Fumis WiRCU device."""
import aiohttp
import pytest
from fumis import Fumis


@pytest.mark.asyncio
async def test_turn_on(event_loop, aresponses):
    """Test turning on Fumis WiRCU device."""
    # Handle to run asserts on request in
    async def response_handler(request):
        data = await request.json()
        assert data == {
            "unit": {"id": "AABBCCDDEEFF", "type": 0, "pin": "1234"},
            "apiVersion": "1",
            "controller": {"command": 2, "type": 0},
        }

        return aresponses.Response(
            status=200, headers={"Content-Type": "application/json"}, text="",
        )

    aresponses.add("api.fumis.si", "/v1/status/", "POST", response_handler)

    async with aiohttp.ClientSession(loop=event_loop) as session:
        fumis = Fumis(
            mac="AABBCCDDEEFF", password="1234", session=session, loop=event_loop,
        )
        await fumis.turn_on()


@pytest.mark.asyncio
async def test_turn_off(event_loop, aresponses):
    """Test turning off Fumis WiRCU device."""
    # Handle to run asserts on request in
    async def response_handler(request):
        data = await request.json()
        assert data == {
            "unit": {"id": "AABBCCDDEEFF", "type": 0, "pin": "1234"},
            "apiVersion": "1",
            "controller": {"command": 1, "type": 0},
        }

        return aresponses.Response(
            status=200, headers={"Content-Type": "application/json"}, text="",
        )

    aresponses.add("api.fumis.si", "/v1/status/", "POST", response_handler)

    async with aiohttp.ClientSession(loop=event_loop) as session:
        fumis = Fumis(
            mac="AABBCCDDEEFF", password="1234", session=session, loop=event_loop,
        )
        await fumis.turn_off()


@pytest.mark.asyncio
async def test_set_target_temperature(event_loop, aresponses):
    """Test setting temperature of a Fumis WiRCU device."""
    # Handle to run asserts on request in
    async def response_handler(request):
        data = await request.json()
        assert data == {
            "unit": {"id": "AABBCCDDEEFF", "type": 0, "pin": "1234"},
            "apiVersion": "1",
            "controller": {"temperatures": [{"set": 23.4, "id": 1}], "type": 0},
        }

        return aresponses.Response(
            status=200, headers={"Content-Type": "application/json"}, text="",
        )

    aresponses.add("api.fumis.si", "/v1/status/", "POST", response_handler)

    async with aiohttp.ClientSession(loop=event_loop) as session:
        fumis = Fumis(
            mac="AABBCCDDEEFF", password="1234", session=session, loop=event_loop,
        )
        await fumis.set_target_temperature(23.4)

@pytest.mark.asyncio
async def test_set_mode(event_loop, aresponses):
    """Test setting mode of a Fumis WiRCU device."""
    # Handle to run asserts on request in
    async def response_handler(request):
        data = await request.json()
        assert data == {
            "unit": {"id": "AABBCCDDEEFF", "type": 0, "pin": "1234"},
            "apiVersion": "1",
            "controller": {"ecoMode": {"ecoModeEnable": 1}},
        }

        return aresponses.Response(
            status=200, headers={"Content-Type": "application/json"}, text="",
        )

    aresponses.add("api.fumis.si", "/v1/status/", "POST", response_handler)

    async with aiohttp.ClientSession(loop=event_loop) as session:
        fumis = Fumis(
            mac="AABBCCDDEEFF", password="1234", session=session, loop=event_loop,
        )
        await fumis.set_mode(1)
