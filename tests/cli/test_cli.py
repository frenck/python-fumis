"""Tests for the Fumis CLI."""

# pylint: disable=redefined-outer-name,protected-access
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import click
import pytest
from typer.main import get_command
from typer.testing import CliRunner

from fumis.cli import cli
from fumis.exceptions import (
    FumisAuthenticationError,
    FumisConnectionError,
    FumisStoveOfflineError,
)
from fumis.models import FumisInfo

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _load_fixture(name: str) -> dict:
    """Load a fixture file and return parsed JSON."""
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def stable_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force deterministic Rich rendering for stable snapshots."""
    monkeypatch.setenv("COLUMNS", "100")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("TERM", "dumb")


@pytest.fixture
def runner() -> CliRunner:
    """Return a CLI runner for invoking the Typer app."""
    return CliRunner()


def _mock_fumis(fixture_name: str) -> MagicMock:
    """Create a mock Fumis client that returns data from a fixture."""
    fixture_data = _load_fixture(fixture_name)
    info = FumisInfo.from_dict(fixture_data)

    client = AsyncMock()
    client.update_info.return_value = info
    client.raw_status.return_value = fixture_data
    client._request.return_value = fixture_data

    instance = AsyncMock()
    instance.__aenter__.return_value = client
    instance.__aexit__.return_value = None

    return MagicMock(return_value=instance)


def _invoke(
    runner: CliRunner,
    args: list[str],
    fixture_name: str = "info.json",
) -> tuple[int, str]:
    """Invoke the CLI with a mocked Fumis client and return the result."""
    mock_cls = _mock_fumis(fixture_name)
    with patch("fumis.cli.Fumis", mock_cls):
        result = runner.invoke(cli, args)
    return result.exit_code, result.stdout


def test_cli_structure(snapshot: SnapshotAssertion) -> None:
    """The CLI exposes the expected commands and options."""
    group = get_command(cli)
    assert isinstance(group, click.Group)
    structure = {
        name: sorted(param.name for param in subcommand.params)
        for name, subcommand in sorted(group.commands.items())
    }
    assert structure == snapshot


def test_info_command(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Info command renders device status panels."""
    exit_code, output = _invoke(
        runner,
        ["info", "--mac", "AABBCCDDEEFF", "--password", "1234"],
    )
    assert exit_code == 0
    assert output == snapshot


def test_info_command_json(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Info command emits JSON when --json is given."""
    exit_code, output = _invoke(
        runner,
        ["info", "--mac", "AABBCCDDEEFF", "--password", "1234", "--json"],
    )
    assert exit_code == 0
    assert output == snapshot


def test_info_clou_duo(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Info command renders Clou Duo hybrid stove details."""
    exit_code, output = _invoke(
        runner,
        ["info", "--mac", "AABB11223344", "--password", "5678"],
        fixture_name="clou_duo_hybrid.json",
    )
    assert exit_code == 0
    assert output == snapshot


def test_info_pellet_stove(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Info command renders unknown pellet stove details."""
    exit_code, output = _invoke(
        runner,
        ["info", "--mac", "REDACTED", "--password", "0000"],
        fixture_name="pellet_stove_unknown.json",
    )
    assert exit_code == 0
    assert output == snapshot


def test_info_error_state(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Info command renders error state correctly."""
    exit_code, output = _invoke(
        runner,
        ["info", "--mac", "AABBCCDDEEFF", "--password", "1234"],
        fixture_name="austroflamm_clou_duo_error.json",
    )
    assert exit_code == 0
    assert output == snapshot


def test_info_combustion_state(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Info command renders combustion state with exhaust temp."""
    exit_code, output = _invoke(
        runner,
        ["info", "--mac", "AABBCCDDEEFF", "--password", "1234"],
        fixture_name="austroflamm_clou_duo_combustion.json",
    )
    assert exit_code == 0
    assert output == snapshot


def test_info_original_fixture(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Info command renders original fixture (no hybrid, no manufacturer)."""
    exit_code, output = _invoke(
        runner,
        ["info", "--mac", "AABBCCDDEEFF", "--password", "1234"],
        fixture_name="info.json",
    )
    assert exit_code == 0
    assert output == snapshot


def test_info_starting_state(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Info command renders starting state (status=off, command=on)."""
    exit_code, output = _invoke(
        runner,
        ["info", "--mac", "AABBCCDDEEFF", "--password", "1234"],
        fixture_name="info_starting.json",
    )
    assert exit_code == 0
    assert output == snapshot


def test_info_alert_state(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Info command renders alert display."""
    exit_code, output = _invoke(
        runner,
        ["info", "--mac", "AABBCCDDEEFF", "--password", "1234"],
        fixture_name="info_alert.json",
    )
    assert exit_code == 0
    assert output == snapshot


def test_info_shutting_down_state(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Info command renders shutting down state (status=cooling, command=off)."""
    exit_code, output = _invoke(
        runner,
        ["info", "--mac", "AABBCCDDEEFF", "--password", "1234"],
        fixture_name="info_shutting_down.json",
    )
    assert exit_code == 0
    assert output == snapshot


def test_errors_no_errors(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Errors command with no active errors."""
    exit_code, output = _invoke(
        runner,
        ["errors", "--mac", "AABBCCDDEEFF", "--password", "1234"],
    )
    assert exit_code == 0
    assert output == snapshot


def test_errors_with_error(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Errors command with active error and history."""
    exit_code, output = _invoke(
        runner,
        ["errors", "--mac", "AABBCCDDEEFF", "--password", "1234"],
        fixture_name="austroflamm_clou_duo_error.json",
    )
    assert exit_code == 0
    assert output == snapshot


def test_errors_with_alert(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Errors command with active alert."""
    exit_code, output = _invoke(
        runner,
        ["errors", "--mac", "AABBCCDDEEFF", "--password", "1234"],
        fixture_name="info_alert.json",
    )
    assert exit_code == 0
    assert output == snapshot


def test_diagnostics_pellet_stove(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Diagnostics command with pellet stove (different sensors)."""
    exit_code, output = _invoke(
        runner,
        ["diagnostics", "--mac", "AABBCCDDEEFF", "--password", "1234"],
        fixture_name="pellet_stove_unknown.json",
    )
    assert exit_code == 0
    assert output == snapshot


def test_on_command(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """On command turns on the stove."""
    exit_code, output = _invoke(
        runner,
        ["on", "--mac", "AABBCCDDEEFF", "--password", "1234"],
    )
    assert exit_code == 0
    assert output == snapshot


def test_off_command(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Off command turns off the stove."""
    exit_code, output = _invoke(
        runner,
        ["off", "--mac", "AABBCCDDEEFF", "--password", "1234"],
    )
    assert exit_code == 0
    assert output == snapshot


def test_temperature_command(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Temperature command sets the target temperature."""
    exit_code, output = _invoke(
        runner,
        ["temperature", "23.5", "--mac", "AABBCCDDEEFF", "--password", "1234"],
    )
    assert exit_code == 0
    assert output == snapshot


def test_temperature_command_with_zone(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Temperature command accepts a zone option."""
    exit_code, output = _invoke(
        runner,
        [
            "temperature",
            "25.0",
            "--mac",
            "AABBCCDDEEFF",
            "--password",
            "1234",
            "--zone",
            "3",
        ],
    )
    assert exit_code == 0
    assert output == snapshot


def test_power_command(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Power command sets the power level."""
    exit_code, output = _invoke(
        runner,
        ["power", "3", "--mac", "AABBCCDDEEFF", "--password", "1234"],
    )
    assert exit_code == 0
    assert output == snapshot


def test_eco_on_command(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Eco command enables eco mode."""
    exit_code, output = _invoke(
        runner,
        ["eco", "true", "--mac", "AABBCCDDEEFF", "--password", "1234"],
    )
    assert exit_code == 0
    assert output == snapshot


def test_eco_off_command(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Eco command disables eco mode."""
    exit_code, output = _invoke(
        runner,
        ["eco", "false", "--mac", "AABBCCDDEEFF", "--password", "1234"],
    )
    assert exit_code == 0
    assert output == snapshot


def test_diagnostics_command(
    runner: CliRunner,
    snapshot: SnapshotAssertion,
) -> None:
    """Diagnostics command renders sensor and IO panels."""
    exit_code, output = _invoke(
        runner,
        ["diagnostics", "--mac", "AABBCCDDEEFF", "--password", "1234"],
        fixture_name="clou_duo_hybrid.json",
    )
    assert exit_code == 0
    assert output == snapshot


def test_dump_command(
    runner: CliRunner,
) -> None:
    """Dump command outputs raw JSON fixture."""
    exit_code, output = _invoke(
        runner,
        ["dump", "--mac", "AABBCCDDEEFF", "--password", "1234"],
    )
    assert exit_code == 0
    # Verify it's valid JSON
    parsed = json.loads(output)
    assert "unit" in parsed
    assert "controller" in parsed


def test_stove_offline_error_handler(
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
) -> None:
    """Stove offline error handler prints a panel and exits with 1."""
    handler = cli.error_handlers[FumisStoveOfflineError]
    with pytest.raises(SystemExit) as exc_info:
        handler(FumisStoveOfflineError("offline"))
    assert exc_info.value.code == 1
    assert capsys.readouterr().out == snapshot


def test_authentication_error_handler(
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
) -> None:
    """Authentication error handler prints a panel and exits with 1."""
    handler = cli.error_handlers[FumisAuthenticationError]
    with pytest.raises(SystemExit) as exc_info:
        handler(FumisAuthenticationError("bad creds"))
    assert exc_info.value.code == 1
    assert capsys.readouterr().out == snapshot


def test_connection_error_handler(
    capsys: pytest.CaptureFixture[str],
    snapshot: SnapshotAssertion,
) -> None:
    """Connection error handler prints a panel and exits with 1."""
    handler = cli.error_handlers[FumisConnectionError]
    with pytest.raises(SystemExit) as exc_info:
        handler(FumisConnectionError("unreachable"))
    assert exc_info.value.code == 1
    assert capsys.readouterr().out == snapshot
