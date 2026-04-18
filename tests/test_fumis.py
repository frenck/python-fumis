"""Tests for the Fumis WiRCU API client."""

# pylint: disable=protected-access
import logging
from datetime import UTC, datetime

import aiohttp
import pytest
from aioresponses import aioresponses
from syrupy.assertion import SnapshotAssertion

from fumis import (
    Fumis,
    FumisAuthenticationError,
    FumisConnectionError,
    FumisConnectionTimeoutError,
    FumisError,
    FumisResponseError,
    FumisStoveOfflineError,
    Info,
    StoveState,
    StoveStatus,
)

from .conftest import load_fixture

API_BASE = "https://api.fumis.si/v1/"
API_ROOT = "https://api.fumis.si/"


# --- Request handling tests ---


async def test_json_request(responses: aioresponses, fumis: Fumis) -> None:
    """Test JSON response is handled correctly."""
    responses.get(
        API_ROOT,
        status=200,
        body='{"test": "ok"}',
        content_type="application/json",
    )
    response = await fumis._request("/")
    assert response is not None
    assert response["test"] == "ok"


async def test_internal_session(responses: aioresponses) -> None:
    """Test internal client session is handled correctly."""
    responses.get(
        API_ROOT,
        status=200,
        body='{"test": "ok"}',
        content_type="application/json",
    )
    async with Fumis(mac="AABBCCDDEEFF", password="1234") as fumis:
        response = await fumis._request("/")
        assert response is not None
        assert response["test"] == "ok"


async def test_request_user_agent(responses: aioresponses, fumis: Fumis) -> None:
    """Test client sending correct user agent headers."""
    responses.get(
        API_ROOT,
        status=200,
        body="{}",
        content_type="application/json",
    )
    await fumis._request("/")
    assert responses.requests is not None
    assert len(responses.requests) == 1
    request_key = next(iter(responses.requests.keys()))
    request = responses.requests[request_key][0]
    assert request.kwargs["headers"]["User-Agent"] == "PythonFumis"


async def test_timeout(responses: aioresponses, fumis: Fumis) -> None:
    """Test request timeout raises FumisConnectionTimeoutError."""
    responses.get(
        API_ROOT,
        exception=TimeoutError(),
    )
    with pytest.raises(FumisConnectionTimeoutError):
        await fumis._request("/")


async def test_timeout_is_connection_error(
    responses: aioresponses, fumis: Fumis
) -> None:
    """Test FumisConnectionTimeoutError inherits from FumisConnectionError."""
    responses.get(
        API_ROOT,
        exception=TimeoutError(),
    )
    with pytest.raises(FumisConnectionError):
        await fumis._request("/")


async def test_invalid_content_type(responses: aioresponses, fumis: Fumis) -> None:
    """Test invalid content type raises FumisResponseError."""
    responses.get(
        API_ROOT,
        status=200,
        body="{}",
        content_type="text/plain",
    )
    with pytest.raises(FumisResponseError):
        await fumis._request("/")


async def test_http_error(responses: aioresponses, fumis: Fumis) -> None:
    """Test HTTP error response handling."""
    responses.get(
        API_ROOT,
        status=502,
        body="Bad Gateway",
        content_type="text/plain",
    )
    with pytest.raises(FumisResponseError):
        await fumis._request("/")


async def test_authentication_error(responses: aioresponses, fumis: Fumis) -> None:
    """Test 401 raises FumisAuthenticationError."""
    responses.get(
        API_ROOT,
        status=401,
        body=load_fixture("error_auth_invalid.json"),
        content_type="application/json",
    )
    with pytest.raises(FumisAuthenticationError):
        await fumis._request("/")


async def test_authentication_error_is_fumis_error(
    responses: aioresponses, fumis: Fumis
) -> None:
    """Test FumisAuthenticationError inherits from FumisError."""
    responses.get(
        API_ROOT,
        status=401,
        body=load_fixture("error_auth_invalid.json"),
        content_type="application/json",
    )
    with pytest.raises(FumisError):
        await fumis._request("/")


async def test_authentication_error_on_update(
    responses: aioresponses, fumis: Fumis
) -> None:
    """Test 401 during update_info clears info and raises."""
    responses.get(
        f"{API_BASE}status",
        status=401,
        body=load_fixture("error_auth_invalid.json"),
        content_type="application/json",
    )
    with pytest.raises(FumisAuthenticationError):
        await fumis.update_info()
    assert fumis.info is None


async def test_stove_offline(responses: aioresponses, fumis: Fumis) -> None:
    """Test 404 raises FumisStoveOfflineError."""
    responses.get(
        API_ROOT,
        status=404,
        body=load_fixture("error_stove_offline.json"),
        content_type="application/json",
    )
    with pytest.raises(FumisStoveOfflineError):
        await fumis._request("/")


async def test_stove_offline_on_update(responses: aioresponses, fumis: Fumis) -> None:
    """Test 404 during update_info clears info and raises."""
    responses.get(
        f"{API_BASE}status",
        status=404,
        body=load_fixture("error_stove_offline.json"),
        content_type="application/json",
    )
    with pytest.raises(FumisStoveOfflineError):
        await fumis.update_info()
    assert fumis.info is None


async def test_server_error(responses: aioresponses, fumis: Fumis) -> None:
    """Test 500 raises FumisResponseError."""
    responses.get(
        API_ROOT,
        status=500,
        body=load_fixture("error_server_error.json"),
        content_type="application/json",
    )
    with pytest.raises(FumisResponseError):
        await fumis._request("/")


async def test_info_none(responses: aioresponses, fumis: Fumis) -> None:
    """Test info data is None when communication has errored."""
    responses.get(
        f"{API_BASE}status",
        status=500,
        body="Internal Server Error",
        content_type="text/plain",
    )
    with pytest.raises(FumisResponseError):
        await fumis.update_info()
    assert fumis.info is None


# --- Snapshot tests: full deserialization of real fixtures ---


async def test_info_original_fixture(
    responses: aioresponses,
    fumis: Fumis,
    snapshot: SnapshotAssertion,
) -> None:
    """Test full deserialization of the original test fixture."""
    responses.get(
        f"{API_BASE}status",
        status=200,
        body=load_fixture("info.json"),
        content_type="application/json",
    )
    info = await fumis.update_info()
    assert info == snapshot


async def test_info_clou_duo_hybrid(
    responses: aioresponses,
    fumis: Fumis,
    snapshot: SnapshotAssertion,
) -> None:
    """Test full deserialization of Austroflamm Clou Duo hybrid fixture."""
    responses.get(
        f"{API_BASE}status",
        status=200,
        body=load_fixture("clou_duo_hybrid.json"),
        content_type="application/json",
    )
    info = await fumis.update_info()
    assert info == snapshot


async def test_info_austroflamm_clou_duo(
    responses: aioresponses,
    fumis: Fumis,
    snapshot: SnapshotAssertion,
) -> None:
    """Test full deserialization of the real Austroflamm Clou Duo fixture."""
    responses.get(
        f"{API_BASE}status",
        status=200,
        body=load_fixture("austroflamm_clou_duo.json"),
        content_type="application/json",
    )
    info = await fumis.update_info()
    assert info == snapshot


async def test_info_austroflamm_clou_duo_error(
    responses: aioresponses,
    fumis: Fumis,
    snapshot: SnapshotAssertion,
) -> None:
    """Test full deserialization of the Clou Duo in error state."""
    responses.get(
        f"{API_BASE}status",
        status=200,
        body=load_fixture("austroflamm_clou_duo_error.json"),
        content_type="application/json",
    )
    info = await fumis.update_info()
    assert info == snapshot
    assert info.controller.error == 102


async def test_info_austroflamm_clou_duo_ignition(
    responses: aioresponses,
    fumis: Fumis,
    snapshot: SnapshotAssertion,
) -> None:
    """Test full deserialization of the Clou Duo during ignition."""
    responses.get(
        f"{API_BASE}status",
        status=200,
        body=load_fixture("austroflamm_clou_duo_ignition.json"),
        content_type="application/json",
    )
    info = await fumis.update_info()
    assert info == snapshot
    assert info.controller.stove_status == StoveStatus.IGNITION


async def test_info_austroflamm_clou_duo_combustion(
    responses: aioresponses,
    fumis: Fumis,
    snapshot: SnapshotAssertion,
) -> None:
    """Test full deserialization of the Clou Duo during combustion."""
    responses.get(
        f"{API_BASE}status",
        status=200,
        body=load_fixture("austroflamm_clou_duo_combustion.json"),
        content_type="application/json",
    )
    info = await fumis.update_info()
    assert info == snapshot
    assert info.controller.stove_status == StoveStatus.COMBUSTION


async def test_info_austroflamm_clou_duo_cooled(
    responses: aioresponses,
    fumis: Fumis,
    snapshot: SnapshotAssertion,
) -> None:
    """Test full deserialization of the Clou Duo after cooling."""
    responses.get(
        f"{API_BASE}status",
        status=200,
        body=load_fixture("austroflamm_clou_duo_cooled.json"),
        content_type="application/json",
    )
    info = await fumis.update_info()
    assert info == snapshot
    assert info.controller.stove_status == StoveStatus.OFF


async def test_info_pellet_stove_unknown(
    responses: aioresponses,
    fumis: Fumis,
    snapshot: SnapshotAssertion,
) -> None:
    """Test full deserialization of an unknown pellet stove fixture."""
    responses.get(
        f"{API_BASE}status",
        status=200,
        body=load_fixture("pellet_stove_unknown.json"),
        content_type="application/json",
    )
    info = await fumis.update_info()
    assert info == snapshot


# --- Fixture-specific assertions ---


async def test_original_fixture_fields(responses: aioresponses, fumis: Fumis) -> None:
    """Test key fields from the original test fixture."""
    responses.get(
        f"{API_BASE}status",
        status=200,
        body=load_fixture("info.json"),
        content_type="application/json",
    )
    info = await fumis.update_info()

    # Unit
    assert info.unit.id == "AABBCCDDEEFF"
    assert info.unit.version == "2.0.0"
    assert info.unit.rssi == -48
    assert info.unit.signal_strength == 100
    assert info.unit.temperature is None

    # Controller
    assert info.controller.stove_status == StoveStatus.OFF
    assert info.controller.on is False
    assert info.controller.alert == 0
    assert info.controller.error == 0

    # Main temperature
    main_temp = info.controller.main_temperature
    assert main_temp is not None
    assert main_temp.actual == 19.9
    assert main_temp.setpoint == 21.8

    # No combustion chamber temp channel (id=7) on this fixture
    assert info.controller.combustion_chamber_temperature is None

    # No hybrid on this stove
    assert info.controller.hybrid is None


async def test_clou_duo_hybrid_fields(responses: aioresponses, fumis: Fumis) -> None:
    """Test fields specific to the Austroflamm Clou Duo hybrid stove."""
    responses.get(
        f"{API_BASE}status",
        status=200,
        body=load_fixture("clou_duo_hybrid.json"),
        content_type="application/json",
    )
    info = await fumis.update_info()

    # This is a hybrid stove
    assert info.controller.hybrid is not None
    assert info.controller.hybrid.actual_type == 1

    # Controller status: pre-heating
    assert info.controller.status == 10
    assert info.controller.stove_status == StoveStatus.PRE_HEATING
    assert info.controller.on is True

    # Has antifreeze enabled
    assert info.controller.antifreeze is not None
    assert info.controller.antifreeze.enable is True
    assert info.controller.antifreeze.temperature == 5

    # Eco mode is on
    assert info.controller.eco_mode is not None
    assert info.controller.eco_mode.enabled is True

    # Has combustion chamber temperature (channel 7)
    assert info.controller.temperature_channel(7) is not None
    assert info.controller.combustion_chamber_temperature == 104

    # Stove identity
    assert info.controller.stove_model == 211
    assert info.controller.parameter_version == 15
    assert info.controller.manufacturer == "Austroflamm"
    assert info.controller.model_name == "Clou Duo"

    # 9 temperature channels on this stove
    assert len(info.controller.temperatures) == 9

    # Fuel quantity
    fuel = info.controller.fuel()
    assert fuel is not None
    assert fuel.quantity == 0.27
    assert fuel.quantity_percentage == 27.0


async def test_pellet_stove_unknown_fields(
    responses: aioresponses, fumis: Fumis
) -> None:
    """Test fields from an unknown brand pellet stove (from issue #20)."""
    responses.get(
        f"{API_BASE}status",
        status=200,
        body=load_fixture("pellet_stove_unknown.json"),
        content_type="application/json",
    )
    info = await fumis.update_info()

    # Controller status: combustion (actively burning)
    assert info.controller.status == 30
    assert info.controller.stove_status == StoveStatus.COMBUSTION

    # Has unit temperature (WiRCU box temp)
    assert info.unit.temperature == 26.5

    # Hybrid is present but inactive
    assert info.controller.hybrid is not None
    assert info.controller.hybrid.actual_type == 0

    # F02 and pressure
    assert info.controller.f02 == 1347
    assert info.controller.pressure == 608

    # Power during combustion
    assert info.controller.power.set_power == 5
    assert info.controller.power.actual_power == 1
    assert info.controller.power.kw == 3.6


# --- Signal strength tests ---


async def test_signal_strength(responses: aioresponses, fumis: Fumis) -> None:
    """Test retrieving Fumis WiRCU device WiFi signal strength."""
    responses.get(
        f"{API_BASE}status",
        status=200,
        body='{"unit": {"rssi": "-60"}}',
        content_type="application/json",
    )
    info = await fumis.update_info()
    assert info.unit.rssi == -60
    assert info.unit.signal_strength == 80


async def test_signal_strength_zero(responses: aioresponses, fumis: Fumis) -> None:
    """Test retrieving Fumis WiRCU device WiFi signal strength with -100 dB."""
    responses.get(
        f"{API_BASE}status",
        status=200,
        body='{"unit": {"rssi": "-100"}}',
        content_type="application/json",
    )
    info = await fumis.update_info()
    assert info.unit.rssi == -100
    assert info.unit.signal_strength == 0


# --- Model helper method tests ---


def test_controller_fan_not_found() -> None:
    """Test fan lookup returns None for missing fan ID."""
    info = Info.from_dict({})
    assert info.controller.fan(99) is None


def test_controller_fuel_not_found() -> None:
    """Test fuel lookup returns None for missing fuel ID."""
    info = Info.from_dict({})
    assert info.controller.fuel(99) is None


def test_controller_temperature_channel_not_found() -> None:
    """Test temperature channel lookup returns None for missing ID."""
    info = Info.from_dict({})
    assert info.controller.temperature_channel(99) is None


def test_controller_main_temperature_empty() -> None:
    """Test main temperature returns None when no temperatures exist."""
    info = Info.from_dict({})
    assert info.controller.main_temperature is None


def test_diagnostic_variable_missing() -> None:
    """Test diagnostic variable lookup returns None for missing ID."""
    info = Info.from_dict({})
    assert info.controller.diagnostic.variable(999) is None


def test_diagnostic_parameter_missing() -> None:
    """Test diagnostic parameter lookup returns None for missing ID."""
    info = Info.from_dict({})
    assert info.controller.diagnostic.parameter(999) is None


def test_fuel_quantity_percentage_none() -> None:
    """Test fuel quantity percentage when quantity is None."""
    info = Info.from_dict({"controller": {"fuels": [{"id": 1}]}})
    fuel = info.controller.fuel()
    assert fuel is not None
    assert fuel.quantity_percentage is None


def test_convenience_properties_none_when_empty() -> None:
    """Test convenience properties return None when no diagnostics exist."""
    info = Info.from_dict({})
    assert info.controller.exhaust_temperature is None
    assert info.controller.door_open is None
    assert info.controller.fan1_speed is None
    assert info.controller.fan2_speed is None
    assert info.controller.f02 is None
    assert info.controller.pressure is None
    assert info.controller.stove_model is None
    assert info.controller.parameter_version is None
    assert info.controller.backwater_temperature is None
    assert info.controller.combustion_chamber_temperature is None
    assert info.controller.model_info is None
    assert info.controller.manufacturer is None
    assert info.controller.model_name is None


def test_unknown_stove_model() -> None:
    """Test unknown stove model returns None for model_info."""
    info = Info.from_dict(
        {
            "controller": {
                "diagnostic": {
                    "variables": [
                        {"id": 96, "value": 999},
                        {"id": 97, "value": 1},
                    ],
                },
            },
        }
    )
    assert info.controller.stove_model == 999
    assert info.controller.model_info is None
    assert info.controller.manufacturer is None
    assert info.controller.model_name is None


def test_door_open_property() -> None:
    """Test door_open returns True when IO4 is 0 (open)."""
    info = Info.from_dict(
        {"controller": {"diagnostic": {"variables": [{"id": 33, "value": 0}]}}}
    )
    assert info.controller.door_open is True


def test_door_closed_property() -> None:
    """Test door_open returns False when IO4 is 1 (closed)."""
    info = Info.from_dict(
        {"controller": {"diagnostic": {"variables": [{"id": 33, "value": 1}]}}}
    )
    assert info.controller.door_open is False


def test_exhaust_temperature_property() -> None:
    """Test exhaust_temperature reads from var[11] (VARIABLE_GASSES_TEMPERATURE)."""
    info = Info.from_dict(
        {"controller": {"diagnostic": {"variables": [{"id": 11, "value": 95}]}}}
    )
    assert info.controller.exhaust_temperature == 95


def test_fan1_speed_property() -> None:
    """Test fan1_speed reads from var[4] (VARIABLE_FAN_1_SPEED)."""
    info = Info.from_dict(
        {"controller": {"diagnostic": {"variables": [{"id": 4, "value": 1200}]}}}
    )
    assert info.controller.fan1_speed == 1200


def test_unknown_status_code() -> None:
    """Test unknown status code returns StoveStatus.UNKNOWN."""
    info = Info.from_dict({"controller": {"status": 999}})
    assert info.controller.stove_status == StoveStatus.UNKNOWN


def test_on_based_on_status() -> None:
    """Test on property is based on status, not command."""
    # Status OFF = not on, regardless of command
    info = Info.from_dict({"controller": {"status": 0, "command": 2}})
    assert info.controller.on is False

    # Status COMBUSTION = on, even with command=1 (normal after ack)
    info = Info.from_dict({"controller": {"status": 30, "command": 1}})
    assert info.controller.on is True

    # Unknown status = not on
    info = Info.from_dict({"controller": {"status": 999}})
    assert info.controller.on is False


def test_stove_state() -> None:
    """Test simplified state derived from raw status."""
    # OFF statuses map to OFF state
    info = Info.from_dict({"controller": {"status": 0}})
    assert info.controller.state == StoveState.OFF

    # PRE_HEATING maps to HEATING_UP
    info = Info.from_dict({"controller": {"status": 10}})
    assert info.controller.state == StoveState.HEATING_UP

    # IGNITION and PRE_COMBUSTION map to IGNITION
    info = Info.from_dict({"controller": {"status": 20}})
    assert info.controller.state == StoveState.IGNITION
    info = Info.from_dict({"controller": {"status": 21}})
    assert info.controller.state == StoveState.IGNITION

    # COMBUSTION maps to BURNING
    info = Info.from_dict({"controller": {"status": 30}})
    assert info.controller.state == StoveState.BURNING

    # ECO maps to ECO
    info = Info.from_dict({"controller": {"status": 40}})
    assert info.controller.state == StoveState.ECO

    # COOLING maps to COOLING
    info = Info.from_dict({"controller": {"status": 50}})
    assert info.controller.state == StoveState.COOLING

    # WOOD_COMBUSTION maps to BURNING
    info = Info.from_dict({"controller": {"status": 110}})
    assert info.controller.state == StoveState.BURNING

    # Unknown maps to UNKNOWN
    info = Info.from_dict({"controller": {"status": 999}})
    assert info.controller.state == StoveState.UNKNOWN

    # StrEnum serializes cleanly
    assert str(StoveState.BURNING) == "burning"


def test_eco_mode_enabled() -> None:
    """Test eco mode enabled/disabled detection."""
    info = Info.from_dict(
        {"controller": {"ecoMode": {"ecoModeEnable": 1, "ecoModeSetType": 1}}}
    )
    assert info.controller.eco_mode is not None
    assert info.controller.eco_mode.enabled is True

    info2 = Info.from_dict(
        {"controller": {"ecoMode": {"ecoModeEnable": 0, "ecoModeSetType": 1}}}
    )
    assert info2.controller.eco_mode is not None
    assert info2.controller.eco_mode.enabled is False


def test_eco_mode_not_enabled() -> None:
    """Test eco mode defaults to disabled."""
    info = Info.from_dict({})
    assert info.controller.eco_mode is None


def test_combustion_chamber_temp_from_channel() -> None:
    """Test combustion chamber temp from temperature channel 7."""
    info = Info.from_dict(
        {
            "controller": {
                "temperatures": [
                    {
                        "id": 7,
                        "actual": 350.0,
                        "set": 0,
                        "onMainScreen": False,
                        "actualType": 10,
                        "setType": 0,
                    },
                ],
            },
        }
    )
    assert info.controller.combustion_chamber_temperature == 350.0


# --- Command tests ---


async def test_turn_on(responses: aioresponses, fumis: Fumis) -> None:
    """Test turning on Fumis WiRCU device."""
    responses.post(
        f"{API_BASE}status",
        status=200,
        body="{}",
        content_type="application/json",
    )
    await fumis.turn_on()


async def test_turn_off(responses: aioresponses, fumis: Fumis) -> None:
    """Test turning off Fumis WiRCU device."""
    responses.post(
        f"{API_BASE}status",
        status=200,
        body="{}",
        content_type="application/json",
    )
    await fumis.turn_off()


async def test_set_target_temperature(responses: aioresponses, fumis: Fumis) -> None:
    """Test setting temperature of a Fumis WiRCU device."""
    responses.post(
        f"{API_BASE}status",
        status=200,
        body="{}",
        content_type="application/json",
    )
    await fumis.set_target_temperature(23.4)


async def test_set_target_temperature_with_id(
    responses: aioresponses, fumis: Fumis
) -> None:
    """Test setting temperature with a specific temperature zone ID."""
    responses.post(
        f"{API_BASE}status",
        status=200,
        body="{}",
        content_type="application/json",
    )
    await fumis.set_target_temperature(25.0, temperature_id=3)


async def test_set_eco_mode(responses: aioresponses, fumis: Fumis) -> None:
    """Test setting eco mode on Fumis WiRCU device."""
    responses.post(
        f"{API_BASE}status",
        status=200,
        body="{}",
        content_type="application/json",
    )
    await fumis.set_eco_mode(enabled=True)


async def test_set_power(responses: aioresponses, fumis: Fumis) -> None:
    """Test setting power level of Fumis WiRCU device."""
    responses.post(
        f"{API_BASE}status",
        status=200,
        body="{}",
        content_type="application/json",
    )
    await fumis.set_power(3)


async def test_set_timer(responses: aioresponses, fumis: Fumis) -> None:
    """Test enabling/disabling the weekly timer."""
    responses.post(
        f"{API_BASE}status",
        status=200,
        body="{}",
        content_type="application/json",
    )
    await fumis.set_timer(enabled=True)


async def test_set_delayed_start(responses: aioresponses, fumis: Fumis) -> None:
    """Test scheduling a delayed start."""
    responses.post(
        f"{API_BASE}status",
        status=200,
        body="{}",
        content_type="application/json",
    )
    at = datetime(2026, 4, 17, 21, 0, 0, tzinfo=UTC)
    await fumis.set_delayed_start(at=at)


async def test_set_delayed_start_clear(responses: aioresponses, fumis: Fumis) -> None:
    """Test clearing a delayed start."""
    responses.post(
        f"{API_BASE}status",
        status=200,
        body="{}",
        content_type="application/json",
    )
    await fumis.set_delayed_start(at=None)


async def test_set_delayed_stop(responses: aioresponses, fumis: Fumis) -> None:
    """Test scheduling a delayed stop."""
    responses.post(
        f"{API_BASE}status",
        status=200,
        body="{}",
        content_type="application/json",
    )
    at = datetime(2026, 4, 17, 22, 0, 0, tzinfo=UTC)
    await fumis.set_delayed_stop(at=at)


async def test_set_fan_speed(responses: aioresponses, fumis: Fumis) -> None:
    """Test setting fan speed."""
    responses.post(
        f"{API_BASE}status",
        status=200,
        body="{}",
        content_type="application/json",
    )
    await fumis.set_fan_speed(speed=3)


async def test_set_fuel_quality(responses: aioresponses, fumis: Fumis) -> None:
    """Test setting fuel quality."""
    responses.post(
        f"{API_BASE}status",
        status=200,
        body="{}",
        content_type="application/json",
    )
    await fumis.set_fuel_quality(quality=2)


async def test_set_fuel_quantity_display(responses: aioresponses, fumis: Fumis) -> None:
    """Test setting fuel quantity display mode."""
    responses.post(
        f"{API_BASE}status",
        status=200,
        body="{}",
        content_type="application/json",
    )
    await fumis.set_fuel_quantity_display(display=1)


def test_schedule_from_timers() -> None:
    """Test parsing the weekly schedule from diagnostic timers."""
    info = Info.from_dict(
        {
            "controller": {
                "timerEnable": True,
                "diagnostic": {
                    "timers": [
                        {"id": 0, "value": 21},
                        {"id": 1, "value": 0},
                        {"id": 2, "value": 22},
                        {"id": 3, "value": 10},
                        {"id": 16, "value": 1},
                        {"id": 18, "value": 1},
                        {"id": 20, "value": 1},
                        {"id": 22, "value": 1},
                        {"id": 24, "value": 1},
                    ],
                },
            }
        }
    )
    c = info.controller
    assert c.timer_enable is True
    schedule = c.schedule

    # Program 1 is 21:00-22:10
    assert schedule.programs[0].active is True
    assert str(schedule.programs[0]) == "21:00-22:10"

    # Programs 2-4 are inactive
    assert schedule.programs[1].active is False
    assert schedule.programs[2].active is False
    assert schedule.programs[3].active is False

    # Monday-Friday enabled, weekend off
    assert schedule.active_days == [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
    ]
    assert schedule.days["saturday"] == (False, False)
    assert schedule.days["sunday"] == (False, False)


def test_schedule_empty() -> None:
    """Test schedule with no timers set."""
    info = Info.from_dict({})
    schedule = info.controller.schedule
    assert all(not p.active for p in schedule.programs)
    assert schedule.active_days == []


async def test_raw_status(responses: aioresponses, fumis: Fumis) -> None:
    """Test raw_status returns the unprocessed API response."""
    responses.get(
        f"{API_BASE}status",
        status=200,
        body=load_fixture("info.json"),
        content_type="application/json",
    )
    data = await fumis.raw_status()
    assert isinstance(data, dict)
    assert "unit" in data
    assert "controller" in data
    assert data["unit"]["id"] == "AABBCCDDEEFF"


def test_eco_mode_unexpected_value() -> None:
    """Test eco mode treats unexpected values as disabled."""
    info = Info.from_dict(
        {"controller": {"ecoMode": {"ecoModeEnable": 99, "ecoModeSetType": 1}}}
    )
    assert info.controller.eco_mode is not None
    assert info.controller.eco_mode.enabled is False


async def test_logging_on_request(
    responses: aioresponses,
    fumis: Fumis,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that debug logging emits request and response info."""
    caplog.set_level(logging.DEBUG, logger="fumis.fumis")
    responses.get(
        f"{API_BASE}status",
        status=200,
        body=load_fixture("info.json"),
        content_type="application/json",
    )
    await fumis.update_info()
    assert "GET https://api.fumis.si/v1/status" in caplog.text
    assert "returned 200" in caplog.text
    assert "Updated info: status=OFF" in caplog.text


async def test_logging_on_timeout(
    responses: aioresponses,
    fumis: Fumis,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that timeout is logged."""
    caplog.set_level(logging.DEBUG, logger="fumis.fumis")
    responses.get(
        API_ROOT,
        exception=TimeoutError(),
    )
    with pytest.raises(FumisConnectionTimeoutError):
        await fumis._request("/")
    assert "Timeout" in caplog.text


async def test_logging_on_command(
    responses: aioresponses,
    fumis: Fumis,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that commands are logged."""
    caplog.set_level(logging.DEBUG, logger="fumis.fumis")
    responses.post(
        f"{API_BASE}status",
        status=200,
        body="{}",
        content_type="application/json",
    )
    await fumis.turn_on()
    assert "Sending command" in caplog.text
    assert "'command': 2" in caplog.text


def test_credentials_not_in_repr() -> None:
    """Test that MAC and password are not exposed in repr."""
    fumis = Fumis(mac="AABBCCDDEEFF", password="secret123")
    assert "secret123" not in repr(fumis)
    assert "AABBCCDDEEFF" not in repr(fumis)


async def test_credentials_not_in_logs(
    responses: aioresponses,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that MAC and password never appear in log output."""
    caplog.set_level(logging.DEBUG, logger="fumis.fumis")
    responses.get(
        f"{API_BASE}status",
        status=200,
        body=load_fixture("info.json"),
        content_type="application/json",
    )
    responses.post(
        f"{API_BASE}status",
        status=200,
        body="{}",
        content_type="application/json",
    )
    async with aiohttp.ClientSession() as session:
        fumis = Fumis(mac="SENSITIVEMAC", password="SECRETPIN", session=session)
        await fumis.update_info()
        await fumis.turn_on()

    assert "SENSITIVEMAC" not in caplog.text
    assert "SECRETPIN" not in caplog.text
