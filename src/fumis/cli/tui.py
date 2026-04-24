"""Live TUI dashboard for the Fumis WiRCU."""

# pylint: disable=import-error,too-few-public-methods
from __future__ import annotations

import asyncio
from collections import deque
from typing import TYPE_CHECKING, ClassVar

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Label, Static
from textual_plotext import PlotextPlot

from fumis.const import StoveAlert, StoveError, StoveStatus
from fumis.fumis import Fumis

if TYPE_CHECKING:
    from fumis.models import FumisInfo

POLL_INTERVAL = 30
MAX_HISTORY = 120


STATUS_ICONS: dict[StoveStatus, str] = {
    StoveStatus.OFF: "\u2b58",
    StoveStatus.PRE_HEATING: "\u25b2",
    StoveStatus.IGNITION: "\U0001f525",
    StoveStatus.PRE_COMBUSTION: "\U0001f525",
    StoveStatus.COMBUSTION: "\U0001f525",
    StoveStatus.ECO: "\U0001f331",
    StoveStatus.COOLING: "\u2744\ufe0f",
    StoveStatus.WOOD_COMBUSTION: "\U0001fab5",
}


class StatusWidget(Static):
    """Displays the current stove status."""

    def update_info(self, info: FumisInfo) -> None:
        """Update the display with new info."""
        c = info.controller
        status = c.stove_status
        icon = STATUS_ICONS.get(status, "\u2753")

        status_label = status.name.replace("_", " ").title()

        main_temp = c.main_temperature
        temp_str = ""
        if main_temp:
            temp_str = f"{main_temp.actual}\u00b0 \u2192 {main_temp.setpoint}\u00b0"

        combustion = c.combustion_chamber_temperature
        combustion_str = f"{combustion}\u00b0" if combustion is not None else ""

        fuel = c.fuel()
        fuel_pct = (fuel.quantity_percentage or 0) if fuel else 0
        fuel_bar = "\u2588" * int(fuel_pct / 10) + "\u2591" * (10 - int(fuel_pct / 10))

        power_str = f"{c.power.kw} kW (level {c.power.set_power})"

        door = c.door_open
        door_str = ""
        if door is not None:
            door_str = "\U0001f6aa Closed" if not door else "\u26a0\ufe0f  OPEN"

        eco = c.eco_mode
        eco_str = ""
        if eco:
            eco_str = "\U0001f331 On" if eco.enabled else "Off"

        error_str = ""
        if error := c.stove_error:
            label = f"E{c.error}" if error == StoveError.UNKNOWN else str(error)
            error_str = f"\u274c {label}: {error.description}"
        if alert := c.stove_alert:
            label = f"A{c.alert:03d}" if alert == StoveAlert.UNKNOWN else str(alert)
            error_str += f"  \u26a0\ufe0f  {label}: {alert.description}"

        lines = [
            f"  {icon}  [bold]{status_label}[/bold]",
            "",
            f"  \U0001f321\ufe0f  Temperature   {temp_str}",
            f"  \U0001f525 Combustion    {combustion_str}",
            f"  \u26a1 Power         {power_str}",
            f"  \u26fd Fuel          {fuel_bar} {fuel_pct:.0f}%",
        ]

        if door_str:
            lines.append(f"  \U0001f6aa Door          {door_str}")
        if eco_str:
            lines.append(f"  \U0001f331 Eco           {eco_str}")
        if error_str:
            lines.append(f"  {error_str}")

        self.update("\n".join(lines))


class InfoWidget(Static):
    """Displays device info and network stats."""

    def update_info(self, info: FumisInfo) -> None:
        """Update the display with new info."""
        c = info.controller
        u = info.unit

        manufacturer = c.manufacturer or ""
        model = c.model_name or f"Model {c.stove_model}" if c.stove_model else ""
        title = f"{manufacturer} {model}".strip() or "Fumis WiRCU"

        stats = c.statistic
        lines = [
            f"  [bold]\U0001f3ed {title}[/bold]",
            f"  [dim]{u.id}[/dim]",
            "",
            f"  \U0001f4f6 WiFi     {u.rssi} dBm ({u.signal_strength}%)",
            f"  \U0001f4e1 IP       {u.ip}",
            "",
            f"  \U0001f504 Starts   {stats.igniter_starts}",
            f"  \U0001f525 Heating  {int(stats.heating_time.total_seconds()) // 3600}h",
            f"  \u23f1\ufe0f  Uptime  {int(stats.uptime.total_seconds()) // 3600}h",
            f"  \U0001f527 Service  in {c.time_to_service}h"
            if c.time_to_service is not None
            else "  \U0001f527 Service  N/A",
        ]

        self.update("\n".join(lines))


class TemperatureDialog(ModalScreen[float | None]):
    """Keyboard-only dialog for setting the target temperature."""

    CSS = """
    TemperatureDialog {
        align: center middle;
    }
    .modal-box {
        width: 36;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    .modal-box Label {
        width: 100%;
        text-align: center;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("up", "adjust(0.5)", show=False),
        Binding("down", "adjust(-0.5)", show=False),
        Binding("+", "adjust(0.1)", show=False),
        Binding("-", "adjust(-0.1)", show=False),
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Confirm"),
    ]

    def __init__(self, current_temp: float) -> None:
        """Initialize with the current target temperature."""
        super().__init__()
        self._temp = current_temp

    def compose(self) -> ComposeResult:
        """Create the dialog layout."""
        with Vertical(classes="modal-box"):
            yield Label("\U0001f321\ufe0f  [bold]Set Temperature[/bold]")
            yield Label("")
            yield Label(
                f"[bold cyan]{self._temp:.1f}\u00b0[/bold cyan]",
                id="temp-value",
            )
            yield Label("")
            yield Label(
                "[dim]\u2191\u2193 \u00b10.5  +/- \u00b10.1[/dim]\n"
                "[dim]Enter confirm \u2022 Esc cancel[/dim]"
            )

    def action_adjust(self, delta: float) -> None:
        """Adjust the temperature."""
        self._temp = round(self._temp + delta, 1)
        self.query_one("#temp-value", Label).update(
            f"[bold cyan]{self._temp:.1f}\u00b0[/bold cyan]"
        )

    def action_confirm(self) -> None:
        """Confirm."""
        self.dismiss(self._temp)

    def action_cancel(self) -> None:
        """Cancel."""
        self.dismiss(None)


class PowerDialog(ModalScreen[int | None]):
    """Keyboard-only dialog for setting the power level."""

    CSS = """
    PowerDialog {
        align: center middle;
    }
    .modal-box {
        width: 36;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    .modal-box Label {
        width: 100%;
        text-align: center;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("up", "adjust(1)", show=False),
        Binding("down", "adjust(-1)", show=False),
        Binding("+", "adjust(1)", show=False),
        Binding("-", "adjust(-1)", show=False),
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "confirm", "Confirm"),
    ]

    def __init__(self, current_level: int) -> None:
        """Initialize with the current power level."""
        super().__init__()
        self._level = current_level

    def _level_display(self) -> str:
        filled = "\u2588" * self._level
        empty = "\u2591" * (5 - self._level)
        return f"[bold yellow]{filled}{empty}  {self._level}/5[/bold yellow]"

    def compose(self) -> ComposeResult:
        """Create the dialog layout."""
        with Vertical(classes="modal-box"):
            yield Label("\u26a1 [bold]Set Power Level[/bold]")
            yield Label("")
            yield Label(self._level_display(), id="power-value")
            yield Label("")
            yield Label(
                "[dim]\u2191\u2193 +/- adjust \u2022 Enter confirm[/dim]\n"
                "[dim]Esc cancel[/dim]"
            )

    def action_adjust(self, delta: int) -> None:
        """Adjust the power level."""
        self._level = max(1, min(5, self._level + delta))
        self.query_one("#power-value", Label).update(self._level_display())

    def action_confirm(self) -> None:
        """Confirm."""
        self.dismiss(self._level)

    def action_cancel(self) -> None:
        """Cancel."""
        self.dismiss(None)


class ConfirmDialog(ModalScreen[bool]):
    """Keyboard-only confirmation dialog."""

    CSS = """
    ConfirmDialog {
        align: center middle;
    }
    .modal-box {
        width: 36;
        height: auto;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    .modal-box Label {
        width: 100%;
        text-align: center;
    }
    """

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("enter", "yes", show=False),
        Binding("y", "yes", show=False),
        Binding("escape", "no", "Cancel"),
        Binding("n", "no", show=False),
    ]

    def __init__(self, icon: str, message: str) -> None:
        """Initialize the dialog."""
        super().__init__()
        self._icon = icon
        self._message = message

    def compose(self) -> ComposeResult:
        """Create the dialog layout."""
        with Vertical(classes="modal-box"):
            yield Label(f"{self._icon}  [bold]{self._message}[/bold]")
            yield Label("")
            yield Label("[dim]Enter/y confirm \u2022 Esc/n cancel[/dim]")

    def action_yes(self) -> None:
        """Confirm."""
        self.dismiss(result=True)

    def action_no(self) -> None:
        """Cancel."""
        self.dismiss(result=False)


class FumisTuiApp(App[None]):
    """Live dashboard for Fumis WiRCU stoves."""

    CSS = """
    Screen {
        layout: vertical;
    }
    #top {
        layout: horizontal;
        height: 14;
    }
    #status-panel {
        width: 1fr;
        border: round green;
        padding: 1;
    }
    #info-panel {
        width: 1fr;
        border: round $primary-lighten-2;
        padding: 1;
    }
    #room-graph {
        height: 1fr;
        min-height: 8;
        border: round cyan;
    }
    #combustion-graph {
        height: 1fr;
        min-height: 8;
        border: round red;
    }
    #room-plot, #combustion-plot {
        height: 1fr;
    }
    #status-bar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    TITLE = "\U0001f525 Fumis WiRCU"
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("1", "turn_on", "Turn On"),
        Binding("0", "turn_off", "Turn Off"),
        Binding("t", "set_temp", "Temperature"),
        Binding("p", "set_power", "Power"),
    ]

    def __init__(self, mac: str, password: str) -> None:
        """Initialize the app."""
        super().__init__()
        self.mac = mac
        self.password = password
        self._info: FumisInfo | None = None
        self._room_history: deque[float] = deque(maxlen=MAX_HISTORY)
        self._target_history: deque[float] = deque(maxlen=MAX_HISTORY)
        self._combustion_history: deque[float] = deque(maxlen=MAX_HISTORY)
        self._poll_count = 0

    def compose(self) -> ComposeResult:
        """Create the layout."""
        yield Header()
        with Horizontal(id="top"):
            with Container(id="status-panel"):
                yield Label("[bold]Status[/bold]")
                yield StatusWidget(id="status")
            with Container(id="info-panel"):
                yield Label("[bold]Device[/bold]")
                yield InfoWidget(id="info")
        with Container(id="room-graph"):
            yield PlotextPlot(id="room-plot")
        with Container(id="combustion-graph"):
            yield PlotextPlot(id="combustion-plot")
        yield Label("  Polling...", id="status-bar")
        yield Footer()

    def _update_graph(self) -> None:
        """Redraw the temperature graphs."""
        # Room temperature graph
        room_widget = self.query_one("#room-plot", PlotextPlot)
        plt = room_widget.plt
        plt.clear_figure()
        plt.theme("dark")
        plt.title("\U0001f321\ufe0f  Room Temperature")
        plt.ylabel("\u00b0C")

        if self._room_history:
            x = list(range(len(self._room_history)))
            plt.plot(
                x,
                list(self._room_history),
                label=f"Actual {self._room_history[-1]}\u00b0",
                color="cyan",
            )
        if self._target_history:
            target = self._target_history[-1]
            plt.hline(target, color="green")
            plt.text(
                f"Target {target}\u00b0",
                0,
                target,
                color="green",
            )

        room_widget.refresh()

        # Combustion chamber graph
        comb_widget = self.query_one("#combustion-plot", PlotextPlot)
        plt2 = comb_widget.plt
        plt2.clear_figure()
        plt2.theme("dark")
        plt2.title("\U0001f525 Combustion Chamber")
        plt2.ylabel("\u00b0C")

        if self._combustion_history:
            x = list(range(len(self._combustion_history)))
            plt2.plot(
                x,
                list(self._combustion_history),
                label=f"{self._combustion_history[-1]}\u00b0",
                color="red",
            )

        comb_widget.refresh()

    def on_mount(self) -> None:
        """Start polling on mount."""
        self._poll()
        self.set_interval(POLL_INTERVAL, self._poll)

    @work(exclusive=True)
    async def _poll(self) -> None:
        """Fetch status from the API."""
        status_bar = self.query_one("#status-bar", Label)
        try:
            async with Fumis(mac=self.mac, password=self.password) as fumis:
                self._info = await fumis.update_info()
            self.query_one("#status", StatusWidget).update_info(self._info)
            self.query_one("#info", InfoWidget).update_info(self._info)

            # Collect temperature history
            c = self._info.controller
            main_temp = c.main_temperature
            if main_temp:
                self._room_history.append(main_temp.actual)
                self._target_history.append(main_temp.setpoint)
            combustion = c.combustion_chamber_temperature
            if combustion is not None:
                self._combustion_history.append(combustion)

            self._update_graph()
            self._poll_count += 1

            status_bar.update(
                f"  Poll #{self._poll_count} \u2022 every {POLL_INTERVAL}s"
                "  \u2022  [dim]1[/dim] on  [dim]0[/dim] off"
                "  [dim]t[/dim] temp  [dim]p[/dim] power"
                "  [dim]r[/dim] refresh  [dim]q[/dim] quit"
            )
        except Exception as err:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            status_bar.update(f"  [red]\u26a0\ufe0f  {err}[/red]")

    @work(exclusive=True)
    async def _send_command(self, action: str) -> None:
        """Send a command and refresh."""
        status_bar = self.query_one("#status-bar", Label)
        status_widget = self.query_one("#status", StatusWidget)

        # Show sending state and force repaint
        label = action.replace("_", " ").title()
        status_bar.update(f"  [yellow bold]\u23f3 Sending: {label}\u2026[/yellow bold]")
        status_widget.update(f"\n  [yellow bold]\u23f3 {label}\u2026[/yellow bold]\n")
        # Yield to let the UI repaint before the blocking API call
        await asyncio.sleep(0.05)

        try:
            async with Fumis(mac=self.mac, password=self.password) as fumis:
                if action == "on":
                    await fumis.turn_on()
                elif action == "off":
                    await fumis.turn_off()
        except Exception as err:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            status_bar.update(f"  [red]\u26a0\ufe0f  {err}[/red]")
            return

        status_bar.update(
            f"  [green]\u2705 {label} sent![/green]"
            "  [dim]Waiting for stove to update\u2026[/dim]"
        )
        await asyncio.sleep(3)
        self._poll()

    def action_refresh(self) -> None:
        """Manual refresh."""
        self._poll()

    def action_turn_on(self) -> None:
        """Confirm and turn on the stove."""

        def _on_dismiss(confirmed: bool) -> None:
            if confirmed:
                self._send_command("on")

        self.push_screen(  # ty: ignore[no-matching-overload]
            ConfirmDialog("\U0001f525", "Turn on the stove?"),
            _on_dismiss,
        )

    def action_turn_off(self) -> None:
        """Confirm and turn off the stove."""

        def _on_dismiss(confirmed: bool) -> None:
            if confirmed:
                self._send_command("off")

        self.push_screen(  # ty: ignore[no-matching-overload]
            ConfirmDialog("\u2744\ufe0f", "Turn off the stove?"),
            _on_dismiss,
        )

    def action_set_power(self) -> None:
        """Open the power level dialog."""
        current = 3
        if self._info:
            current = self._info.controller.power.set_power

        def _on_dismiss(result: int | None) -> None:
            if result is not None:
                self._send_power(result)

        self.push_screen(PowerDialog(current), _on_dismiss)

    @work(exclusive=True)
    async def _send_power(self, level: int) -> None:
        """Send the power command."""
        status_bar = self.query_one("#status-bar", Label)
        status_bar.update(
            f"  [yellow bold]\u23f3 Setting power to {level}\u2026[/yellow bold]"
        )
        await asyncio.sleep(0.05)
        try:
            async with Fumis(mac=self.mac, password=self.password) as fumis:
                await fumis.set_power(level)
        except Exception as err:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            status_bar.update(f"  [red]\u26a0\ufe0f  {err}[/red]")
            return
        status_bar.update(
            f"  [green]\u2705 Power set to {level}![/green]"
            "  [dim]Waiting for stove to update\u2026[/dim]"
        )
        await asyncio.sleep(3)
        self._poll()

    def action_set_temp(self) -> None:
        """Open the temperature dialog."""
        current = 20.0
        if self._info:
            main = self._info.controller.main_temperature
            if main:
                current = main.setpoint

        def _on_dismiss(result: float | None) -> None:
            if result is not None:
                self._send_temp(result)

        self.push_screen(TemperatureDialog(current), _on_dismiss)

    @work(exclusive=True)
    async def _send_temp(self, temperature: float) -> None:
        """Send the temperature command."""
        status_bar = self.query_one("#status-bar", Label)
        status_bar.update(
            f"  [yellow bold]\u23f3 Setting temperature to"
            f" {temperature}\u00b0\u2026[/yellow bold]"
        )
        await asyncio.sleep(0.05)
        try:
            async with Fumis(mac=self.mac, password=self.password) as fumis:
                await fumis.set_target_temperature(temperature)
        except Exception as err:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            status_bar.update(f"  [red]\u26a0\ufe0f  {err}[/red]")
            return
        status_bar.update(
            f"  [green]\u2705 Temperature set to {temperature}\u00b0![/green]"
            "  [dim]Waiting for stove to update\u2026[/dim]"
        )
        await asyncio.sleep(3)
        self._poll()
