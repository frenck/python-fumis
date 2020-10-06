"""Models for the Fumis WiRCU."""

import attr

from .const import (
    ECO_MAPPING,
    STATE_MAPPING,
    STATE_UNKNOWN,
    STATUS_MAPPING,
    STATUS_UNKNOWN,
    STOVE_ID,
)


@attr.s(auto_attribs=True, frozen=True)
class Info:
    """Object holding information and states of the Fumis WiRCU device."""

    unit_id: str

    unit_version: str
    controller_version: str

    ip: str
    rssi: int
    signal_strength: int

    state: str
    state_id: int
    status: str
    status_id: int

    temperature: float
    target_temperature: float

    heating_time: int
    igniter_starts: int
    misfires: int
    overheatings: int
    uptime: int
    fuel_quality: int
    fuel_quantity: float
    ecomode_type: int
    ecomode_state: str
    timers: list
    kw: float
    actualpower: float

    @staticmethod
    def from_dict(data: dict):
        """Return device object from Fumis WiRCU device response."""
        controller = data.get("controller", {})
        unit = data.get("unit", {})

        stats = controller.get("statistic", {})
        temperatures = controller.get("temperatures", {})
        power = controller.get("power", {})
        if temperatures:
            temperature = [d for d in temperatures if d["id"] == STOVE_ID][0]
        else:
            temperature = {}
        fuels = controller.get("fuels", [])
        if fuels:
            fuel = [d for d in fuels if d["id"] == STOVE_ID][0]
        else:
            fuel = {}
        ecoMode = controller.get("ecoMode", {})
        timers = controller.get("timers", [])

        rssi = int(unit.get("rssi", -100))
        if rssi <= -100:
            signal_strength = 0
        elif rssi >= -50:
            signal_strength = 100
        else:
            signal_strength = 2 * (rssi + 100)

        status_id = controller.get("status", -1)
        status = STATUS_MAPPING.get(status_id, STATUS_UNKNOWN)

        state_id = controller.get("command", -1)
        state = STATE_MAPPING.get(state_id, STATE_UNKNOWN)

        ecomode_id = ecoMode.get("ecoModeEnable", -1)
        ecomode_state = ECO_MAPPING.get(ecomode_id, STATE_UNKNOWN)

        return Info(
            controller_version=controller.get("version", "Unknown"),
            heating_time=int(stats.get("heatingTime", 0)),
            igniter_starts=stats.get("igniterStarts", 0),
            ip=unit.get("ip", "Unknown"),
            misfires=stats.get("misfires", 0),
            overheatings=stats.get("overheatings", 0),
            rssi=rssi,
            signal_strength=signal_strength,
            state_id=state_id,
            state=state,
            status_id=status_id,
            status=status,
            kw=float(power.get("kw", 0)),
            actualpower=float(power.get("actualPower", 0)),
            target_temperature=temperature.get("set", 0),
            temperature=temperature.get("actual", 0),
            unit_id=unit.get("id", "Unknown"),
            unit_version=unit.get("version", "Unknown"),
            uptime=int(stats.get("uptime", 0)),
            fuel_quality=int(fuel.get("quality", 0)),
            fuel_quantity=(float(fuel.get("quantity", 0)) * 100),
            ecomode_type=int(ecoMode.get("ecoModeSetType", 0)),
            ecomode_state=ecomode_state,
            timers=timers,
        )
