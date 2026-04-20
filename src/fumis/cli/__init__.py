"""Command-line interface for the Fumis WiRCU API."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from fumis.const import StoveStatus
from fumis.exceptions import (
    FumisAuthenticationError,
    FumisConnectionError,
    FumisStoveOfflineError,
)
from fumis.fumis import Fumis

from .async_typer import AsyncTyper

if TYPE_CHECKING:
    from fumis.models import FumisController, FumisInfo

cli = AsyncTyper(
    help="Fumis WiRCU CLI — run without a command to launch the live TUI.",
    invoke_without_command=True,
    no_args_is_help=False,
    add_completion=False,
)
console = Console()

Mac = Annotated[
    str,
    typer.Option(
        help="MAC address of the WiRCU device (uppercase, no colons)",
        prompt="MAC address",
        show_default=False,
        envvar="FUMIS_MAC",
    ),
]
Password = Annotated[
    str,
    typer.Option(
        help="PIN/password of the WiRCU device",
        prompt="Password",
        show_default=False,
        envvar="FUMIS_PASSWORD",
    ),
]
JsonFlag = Annotated[
    bool,
    typer.Option(
        "--json",
        help="Emit machine-readable JSON output",
    ),
]


@cli.callback(invoke_without_command=True)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
def main_callback(
    ctx: typer.Context,
    mac: Annotated[
        str,
        typer.Option(
            help="MAC address (for TUI mode)",
            envvar="FUMIS_MAC",
        ),
    ] = "",
    password: Annotated[
        str,
        typer.Option(
            help="Password/PIN (for TUI mode)",
            envvar="FUMIS_PASSWORD",
        ),
    ] = "",
) -> None:
    """Launch the live TUI when no subcommand is given."""
    if ctx.invoked_subcommand is not None:
        return
    if not mac or not password:  # pragma: no cover
        console.print(
            "[red]MAC and password are required.[/red]\n"
            "Use [bold]--mac[/bold] and [bold]--password[/bold],"
            " or set FUMIS_MAC and FUMIS_PASSWORD env vars.\n"
            "\nRun [bold]fumis --help[/bold] for all commands."
        )
        raise typer.Exit(code=1)
    from fumis.cli.tui import FumisTuiApp  # noqa: PLC0415  # pylint: disable=import-outside-toplevel  # pragma: no cover

    app = FumisTuiApp(mac=mac, password=password)  # pragma: no cover
    app.run()  # pragma: no cover
    raise typer.Exit  # pragma: no cover


@cli.error_handler(FumisStoveOfflineError)
def stove_offline_error_handler(_: FumisStoveOfflineError) -> None:
    """Handle stove offline errors."""
    message = """
    The stove is not connected. The WiRCU module may be powered
    off or unable to reach the cloud. Please check the stove's
    power and WiFi connection.
    """
    panel = Panel(
        message,
        expand=False,
        title="Stove offline",
        border_style="yellow bold",
    )
    console.print(panel)
    sys.exit(1)


@cli.error_handler(FumisAuthenticationError)
def authentication_error_handler(_: FumisAuthenticationError) -> None:
    """Handle authentication errors."""
    message = """
    Invalid MAC address or PIN. Please check your credentials
    and try again.
    """
    panel = Panel(
        message,
        expand=False,
        title="Authentication error",
        border_style="red bold",
    )
    console.print(panel)
    sys.exit(1)


@cli.error_handler(FumisConnectionError)
def connection_error_handler(_: FumisConnectionError) -> None:
    """Handle connection errors."""
    message = """
    Could not connect to the Fumis WiRCU API. Please check your
    internet connection and try again.
    """
    panel = Panel(
        message,
        expand=False,
        title="Connection error",
        border_style="red bold",
    )
    console.print(panel)
    sys.exit(1)


async def _fetch_info(mac: str, password: str) -> FumisInfo:
    """Fetch device info from the Fumis API."""
    async with Fumis(mac=mac, password=password) as fumis:
        return await fumis.update_info()


def _emit_json(payload: object) -> None:
    """Emit a payload as indented JSON on stdout."""
    typer.echo(json.dumps(payload, indent=2, default=str))


STATUS_ICONS: dict[StoveStatus, str] = {
    StoveStatus.OFF: "[dim]\u2b58[/dim]",
    StoveStatus.PRE_HEATING: "[yellow]\u25b2[/yellow]",
    StoveStatus.IGNITION: "[yellow]\U0001f525[/yellow]",
    StoveStatus.PRE_COMBUSTION: "[yellow]\U0001f525[/yellow]",
    StoveStatus.COMBUSTION: "[red]\U0001f525[/red]",
    StoveStatus.ECO: "[green]\U0001f331[/green]",
    StoveStatus.COOLING: "[cyan]\u2744[/cyan]",
    StoveStatus.COLD_START_OFF: "[dim]\u2b58[/dim]",
    StoveStatus.WOOD_BURNING_OFF: "[dim]\u2b58[/dim]",
    StoveStatus.HYBRID_INIT: "[yellow]\u25b2[/yellow]",
    StoveStatus.HYBRID_START: "[yellow]\U0001f525[/yellow]",
    StoveStatus.WOOD_START: "[yellow]\U0001fab5[/yellow]",
    StoveStatus.COLD_START: "[yellow]\u25b2[/yellow]",
    StoveStatus.WOOD_COMBUSTION: "[red]\U0001fab5[/red]",
}


def _status_display(c: FumisController) -> str:
    """Return a formatted status string with icon and state hint."""
    status = c.stove_status
    icon = STATUS_ICONS.get(status, "\u2753")
    label = status.name.replace("_", " ").title()
    return f"{icon}  {label}"


def _render_info(  # noqa: PLR0912, PLR0915  # pylint: disable=too-many-branches,too-many-statements
    info: FumisInfo,
) -> None:
    """Render the full stove info display."""
    c = info.controller

    # Header: stove identity
    if c.manufacturer and c.model_name:
        title = f"\U0001f3ed {c.manufacturer} {c.model_name}"
    elif c.stove_model is not None:
        title = f"\U0001f3ed Model {c.stove_model}"
    else:
        title = "\U0001f3ed Fumis WiRCU"

    console.print()
    console.print(f"  [bold]{title}[/bold]")
    console.print(
        f"  [dim]ID: {info.unit.id} \u2022 "
        f"WiRCU {info.unit.version} \u2022 "
        f"Controller {c.version} \u2022 "
        f"API {info.api_version}[/dim]"
    )
    console.print()

    # Status panel
    status_table = Table(show_header=False, box=None, padding=(0, 2), min_width=50)
    status_table.add_column("Field", style="bold")
    status_table.add_column("Value")

    status_table.add_row("\U0001f3e0 Status", _status_display(c))

    if c.error:
        error_desc = ERROR_DESCRIPTIONS.get(c.error, "Unknown")
        status_table.add_row(
            "\u274c Error",
            f"[red bold]E{c.error}[/red bold] [dim]{error_desc}[/dim]",
        )
    if c.alert:
        alert_desc = ALERT_DESCRIPTIONS.get(c.alert, "Unknown")
        status_table.add_row(
            "\u26a0\ufe0f  Alert",
            f"[yellow bold]A{c.alert:03d}[/yellow bold] [dim]{alert_desc}[/dim]",
        )

    main_temp = c.main_temperature
    if main_temp:
        status_table.add_row(
            "\U0001f321\ufe0f  Temperature",
            f"[bold]{main_temp.actual}\u00b0[/bold] \u2192 {main_temp.setpoint}\u00b0",
        )

    combustion_temp = c.combustion_chamber_temperature
    if combustion_temp is not None:
        status_table.add_row("\U0001f525 Combustion", f"{combustion_temp}\u00b0")

    exhaust_temp = c.exhaust_temperature
    if exhaust_temp is not None and exhaust_temp > 0:
        status_table.add_row("\U0001f4a8 Exhaust", f"{exhaust_temp}\u00b0")

    status_table.add_row("\u26a1 Power", f"{c.power.kw} kW (level {c.power.set_power})")

    fuel = c.fuel()
    pct = fuel.quantity_percentage if fuel else None
    if pct is not None:
        fuel_bar = "\u2588" * int(pct / 10) + "\u2591" * (10 - int(pct / 10))
        status_table.add_row("\u26fd Fuel", f"{fuel_bar} {pct:.0f}%")

    if c.door_open is not None:
        door_icon = "\U0001f6aa" if not c.door_open else "\u26a0\ufe0f "
        door_text = (
            "[red bold]OPEN[/red bold]" if c.door_open else "[green]Closed[/green]"
        )
        status_table.add_row(f"{door_icon} Door", door_text)

    if c.eco_mode:
        eco_icon = "\U0001f331" if c.eco_mode.enabled else "\u2b58"
        eco_text = "[green]On[/green]" if c.eco_mode.enabled else "[dim]Off[/dim]"
        status_table.add_row(f"{eco_icon}  Eco mode", eco_text)

    if c.antifreeze and c.antifreeze.enable is not None:
        af = c.antifreeze
        af_icon = "\u2744\ufe0f" if af.enable else "\u2b58"
        if af.enable:
            af_text = f"[green]On[/green] ({af.temperature}\u00b0)"
        else:
            af_text = "[dim]Off[/dim]"
        status_table.add_row(f"{af_icon}  Antifreeze", af_text)

    if c.hybrid:
        status_table.add_row("\U0001fab5  Hybrid", "Yes")

    console.print(
        Panel(status_table, title="Status", border_style="green", expand=False)
    )

    # Network + Stats side by side
    net_table = Table(show_header=False, box=None, padding=(0, 1))
    net_table.add_column("Field", style="bold dim")
    net_table.add_column("Value", style="dim")
    net_table.add_row("\U0001f4e1 IP", info.unit.ip)
    net_table.add_row(
        "\U0001f4f6 WiFi",
        f"{info.unit.rssi} dBm ({info.unit.signal_strength}%)",
    )
    if info.unit.temperature is not None:
        net_table.add_row("\U0001f321\ufe0f  WiRCU", f"{info.unit.temperature}\u00b0")
    if c.parameter_version is not None:
        net_table.add_row("\U0001f4cb Params", f"v{c.parameter_version}")

    stats = c.statistic
    stats_table = Table(show_header=False, box=None, padding=(0, 1))
    stats_table.add_column("Field", style="bold dim")
    stats_table.add_column("Value", style="dim")
    stats_table.add_row("\U0001f504 Starts", str(stats.igniter_starts))
    stats_table.add_row(
        "\U0001f525 Heating",
        f"{int(stats.heating_time.total_seconds()) // 3600}h",
    )
    stats_table.add_row(
        "\u23f1\ufe0f  Uptime",
        f"{int(stats.uptime.total_seconds()) // 3600}h",
    )
    if c.time_to_service is not None:
        stats_table.add_row("\U0001f527 Service", f"in {c.time_to_service}h")
    if stats.misfires:
        stats_table.add_row(
            "\u26a0\ufe0f  Misfires",
            f"[yellow]{stats.misfires}[/yellow]",
        )
    if stats.overheatings:
        stats_table.add_row(
            "\u26a0\ufe0f  Overheats",
            f"[red]{stats.overheatings}[/red]",
        )

    footer = Table(show_header=False, box=None, padding=(0, 1))
    footer.add_column()
    footer.add_column()
    footer.add_row(
        Panel(
            net_table,
            title="[dim]Network[/dim]",
            border_style="dim",
            expand=False,
        ),
        Panel(
            stats_table,
            title="[dim]Statistics[/dim]",
            border_style="dim",
            expand=False,
        ),
    )
    console.print(footer)


@cli.command("info")
async def info_command(
    mac: Mac,
    password: Password,
    output_json: JsonFlag = False,  # noqa: FBT002
) -> None:
    """Show device information and current status."""
    info = await _fetch_info(mac, password)

    if output_json:
        data = info.to_dict()
        data["unit"]["id"] = "**REDACTED**"
        _emit_json(data)
        return

    _render_info(info)


@cli.command("on")
async def on_command(
    mac: Mac,
    password: Password,
) -> None:
    """Turn on the stove."""
    with console.status("\U0001f525 Turning on..."):
        async with Fumis(mac=mac, password=password) as fumis:
            await fumis.turn_on()
    console.print("\U0001f525 [green bold]Stove turned on.[/green bold]")


@cli.command("off")
async def off_command(
    mac: Mac,
    password: Password,
) -> None:
    """Turn off the stove."""
    with console.status("\u2744\ufe0f  Turning off..."):
        async with Fumis(mac=mac, password=password) as fumis:
            await fumis.turn_off()
    console.print("\u2744\ufe0f  [yellow bold]Stove turned off.[/yellow bold]")


@cli.command("temperature")
async def temperature_command(
    temperature: Annotated[
        float,
        typer.Argument(help="Target temperature in degrees"),
    ],
    mac: Mac,
    password: Password,
    zone: Annotated[
        int,
        typer.Option(
            "--zone",
            "-z",
            help="Temperature zone ID (default: main zone)",
        ),
    ] = 1,
) -> None:
    """Set the target temperature."""
    with console.status(
        f"\U0001f321\ufe0f  Setting temperature to {temperature}\u00b0..."
    ):
        async with Fumis(mac=mac, password=password) as fumis:
            await fumis.set_target_temperature(temperature, temperature_id=zone)
    console.print(
        f"\U0001f321\ufe0f  [green bold]Target temperature set to {temperature}\u00b0"
        f" (zone {zone}).[/green bold]"
    )


@cli.command("power")
async def power_command(
    level: Annotated[
        int,
        typer.Argument(help="Power level (1-5)", min=1, max=5),
    ],
    mac: Mac,
    password: Password,
) -> None:
    """Set the power level (1-5)."""
    with console.status(f"\u26a1 Setting power to {level}..."):
        async with Fumis(mac=mac, password=password) as fumis:
            await fumis.set_power(level)
    console.print(f"\u26a1 [green bold]Power level set to {level}.[/green bold]")


@cli.command("eco")
async def eco_command(
    state: Annotated[
        bool,
        typer.Argument(help="Enable (true) or disable (false) eco mode"),
    ],
    mac: Mac,
    password: Password,
) -> None:
    """Enable or disable eco mode."""
    label = "enabling" if state else "disabling"
    with console.status(f"\U0001f331 {label.title()} eco mode..."):
        async with Fumis(mac=mac, password=password) as fumis:
            await fumis.set_eco_mode(enabled=state)
    result = "enabled" if state else "disabled"
    console.print(f"\U0001f331 [green bold]Eco mode {result}.[/green bold]")


@cli.command("timer")
async def timer_command(
    state: Annotated[
        bool | None,
        typer.Argument(help="Enable (true) or disable (false) timer schedule"),
    ] = None,
    mac: Mac = None,  # type: ignore[assignment]  # ty: ignore[invalid-parameter-default]
    password: Password = None,  # type: ignore[assignment]  # ty: ignore[invalid-parameter-default]
) -> None:
    """Show, enable, or disable the weekly timer schedule.

    Without an argument, shows the current schedule.
    With true/false, enables or disables the timer.
    """
    if state is not None:
        label = "enabling" if state else "disabling"
        with console.status(f"\u23f0 {label.title()} timer..."):
            async with Fumis(mac=mac, password=password) as fumis:
                await fumis.set_timer(enabled=state)
        result = "enabled" if state else "disabled"
        console.print(f"\u23f0 [green bold]Timer {result}.[/green bold]")
        return

    info = await _fetch_info(mac, password)
    c = info.controller
    schedule = c.schedule

    status = "\u2705 Enabled" if c.timer_enable else "\u274c Disabled"
    console.print(f"\u23f0 [bold]Timer:[/bold] {status}")
    console.print()

    # Programs
    table = Table(title="Programs", show_header=True, border_style="dim")
    table.add_column("#", style="bold")
    table.add_column("Schedule")
    for i, prog in enumerate(schedule.programs, 1):
        if prog.active:
            table.add_row(str(i), str(prog))
        else:
            table.add_row(str(i), "[dim]not set[/dim]")
    console.print(table)
    console.print()

    # Days
    day_table = Table(title="Days", show_header=True, border_style="dim")
    day_table.add_column("Day", style="bold")
    day_table.add_column("Slot 1")
    day_table.add_column("Slot 2")
    for day, (s1, s2) in schedule.days.items():
        s1_str = "\u2705" if s1 else "[dim]\u2014[/dim]"
        s2_str = "\u2705" if s2 else "[dim]\u2014[/dim]"
        day_table.add_row(day.capitalize(), s1_str, s2_str)
    console.print(day_table)


@cli.command("sync-clock")
async def sync_clock_command(
    mac: Mac = None,  # type: ignore[assignment]  # ty: ignore[invalid-parameter-default]
    password: Password = None,  # type: ignore[assignment]  # ty: ignore[invalid-parameter-default]
) -> None:
    """Sync the stove's clock to the current time."""
    with console.status("\U0001f552 Syncing clock..."):
        async with Fumis(mac=mac, password=password) as fumis:
            await fumis.set_clock()
    console.print("\U0001f552 [green bold]Clock synced.[/green bold]")


ERROR_DESCRIPTIONS: dict[int, str] = {
    0: "No error",
    101: "Ignition failed / water overtemperature / backfire protection",
    102: "Chimney/burning pot dirty or manually stopped",
    105: "Sensor T02 malfunction",
    106: "Sensor T03/T05 malfunction",
    107: "Sensor T04 malfunction",
    108: "Security switch I01 tripped (STB)",
    109: "Pressure sensor switched OFF",
    110: "Sensor T01/T02 malfunction",
    111: "Sensor T01/T03 malfunction",
    113: "Flue gas overtemperature",
    114: "Fuel ignition timeout / tank empty",
    115: "General error",
    239: "MFDoor Alarm",
    240: "Fire Error",
    241: "Chimney Alarm",
    243: "Grate Error",
    244: "NTC2 Alarm",
    245: "NTC3 Alarm",
    247: "Door Alarm",
    248: "Pressure Alarm",
    249: "NTC1 Alarm",
    250: "TC1 Alarm",
    252: "Gas Alarm",
    253: "No Pellet Alarm",
}

ALERT_DESCRIPTIONS: dict[int, str] = {
    0: "No alert",
    1: "Low fuel level",
    2: "Service due",
    3: "Flue gas temperature warning",
    4: "Low battery",
    5: "Speed sensor failure",
    6: "Door open",
    7: "Airflow sensor malfunction (limited mode)",
}


def _format_error_date(date_val: int, time_val: int) -> str:
    """Format an error history date/time entry."""
    parts: list[str] = []
    if date_val > 20000101:
        d = str(date_val)
        parts.append(f"{d[:4]}-{d[4:6]}-{d[6:]}")
    if time_val:
        parts.append(f"{time_val // 100:02d}:{time_val % 100:02d}")
    return " ".join(parts) or "-"


@cli.command("errors")
async def errors_command(
    mac: Mac = None,  # type: ignore[assignment]  # ty: ignore[invalid-parameter-default]
    password: Password = None,  # type: ignore[assignment]  # ty: ignore[invalid-parameter-default]
) -> None:
    """Show current errors, alerts, and error history."""
    info = await _fetch_info(mac, password)
    c = info.controller

    # Current error
    error_desc = ERROR_DESCRIPTIONS.get(c.error, "Unknown")
    if c.error == 0:
        console.print("\u2705 [green bold]No active error[/green bold]")
    else:
        console.print(f"\u274c [red bold]Error E{c.error}:[/red bold] {error_desc}")

    # Current alert
    alert_desc = ALERT_DESCRIPTIONS.get(c.alert, "Unknown")
    if c.alert == 0:
        console.print("\u2705 [green bold]No active alert[/green bold]")
    else:
        console.print(
            f"\u26a0\ufe0f  [yellow bold]Alert A{c.alert:03d}:[/yellow bold]"
            f" {alert_desc}"
        )

    # Error history from diagnostic variables
    # var[36..95] in groups of 4: [sequence, error_code, date(YYYYMMDD), time]
    diag = c.diagnostic
    history: list[tuple[int, int, int]] = []
    for i in range(15):
        base = 36 + i * 4
        error_code = diag.variable(base + 1)
        if error_code is None or error_code == 0:
            continue
        date_val = diag.variable(base + 2) or 0
        time_val = diag.variable(base + 3) or 0
        history.append((error_code, date_val, time_val))

    if not history:
        console.print("\n[dim]No error history.[/dim]")
        return

    console.print()
    table = Table(title="Error History", show_header=True, border_style="dim")
    table.add_column("#", style="bold")
    table.add_column("Code")
    table.add_column("Description")
    table.add_column("Date")
    for i, (code, date_val, time_val) in enumerate(history, 1):
        desc = ERROR_DESCRIPTIONS.get(code, f"Unknown ({code})")
        table.add_row(str(i), f"E{code}", desc, _format_error_date(date_val, time_val))
    console.print(table)


@cli.command("diagnostics")
async def diagnostics_command(
    mac: Mac,
    password: Password,
) -> None:
    """Show service diagnostics (like the app's service info screen)."""
    info = await _fetch_info(mac, password)
    c = info.controller

    # Sensors panel
    sensors = Table(show_header=False, expand=True)
    sensors.add_column("Field", style="bold")
    sensors.add_column("Value")

    if c.fan1_speed is not None:
        sensors.add_row("Fan 1 speed", str(c.fan1_speed))
    if c.fan2_speed is not None:
        sensors.add_row("Fan 2 speed", str(c.fan2_speed))
    if c.exhaust_temperature is not None:
        sensors.add_row("Exhaust gas temp", f"{c.exhaust_temperature}°")
    if c.combustion_chamber_temperature is not None:
        sensors.add_row("Combustion chamber", f"{c.combustion_chamber_temperature}°")
    if c.f02 is not None:
        sensors.add_row("F02", str(c.f02))
    if c.pressure is not None:
        sensors.add_row("Pressure", str(c.pressure))

    sensors.add_row("Power (kW)", str(c.power.kw))
    sensors.add_row("Power level", str(c.power.set_power))

    console.print(Panel(sensors, title="Sensors", border_style="cyan"))

    # IO inputs panel
    io_table = Table(show_header=False, expand=True)
    io_table.add_column("Input", style="bold")
    io_table.add_column("State")

    io_names = {30: "IO1 (STB)", 31: "IO2", 32: "IO3", 33: "IO4 (Door)"}
    for var_id, name in io_names.items():
        val = c.diagnostic.variable(var_id)
        if val is not None:
            state = "[green]ON[/green]" if val else "[red]OFF[/red]"
            io_table.add_row(name, state)

    console.print(Panel(io_table, title="Digital Inputs", border_style="cyan"))

    # Temperature channels panel
    temp_table = Table(expand=True)
    temp_table.add_column("ID", style="cyan bold", justify="right")
    temp_table.add_column("Actual", justify="right")
    temp_table.add_column("Setpoint", justify="right")
    temp_table.add_column("On screen")
    temp_table.add_column("Type")

    for temp in c.temperatures:
        on_screen = "yes" if temp.on_main_screen else ""
        actual_type = str(temp.actual_type) if temp.actual_type else ""
        temp_table.add_row(
            str(temp.id),
            f"{temp.actual}°" if temp.actual else "",
            f"{temp.setpoint}°" if temp.setpoint else "",
            on_screen,
            actual_type,
        )

    console.print(Panel(temp_table, title="Temperature Channels", border_style="cyan"))


@cli.command("dump")
async def dump_command(
    mac: Mac,
    password: Password,
) -> None:
    """Dump the raw API response as JSON (useful for debugging/fixtures)."""
    async with Fumis(mac=mac, password=password) as fumis:
        data = await fumis.raw_status()
    if "unit" in data and "id" in data["unit"]:
        data["unit"]["id"] = "**REDACTED**"
    typer.echo(json.dumps(data, indent=2, default=str))
