# pylint: disable=W0621
"""Example: Read and control the weekly timer schedule."""

import asyncio

from fumis import Fumis


async def main() -> None:
    """Show the timer schedule and toggle it."""
    async with Fumis(mac="AABBCCDDEEFF", password="1234") as fumis:
        info = await fumis.update_info()

        # Timer master switch
        print(f"Timer enabled: {info.controller.timer_enable}")

        # Weekly schedule (parsed from diagnostic timers)
        schedule = info.controller.schedule

        # Show active programs
        for i, prog in enumerate(schedule.programs, 1):
            if prog.active:
                print(f"  Program {i}: {prog}")  # e.g. "21:00-22:10"

        # Show which days are enabled
        print(f"Active days: {schedule.active_days}")

        # Per-day detail
        for day, (slot1, slot2) in schedule.days.items():
            if slot1 or slot2:
                s1 = "on" if slot1 else "off"
                s2 = "on" if slot2 else "off"
                print(f"  {day}: slot1={s1} slot2={s2}")

        # Enable/disable the timer
        await fumis.set_timer(enabled=True)
        await fumis.set_timer(enabled=False)


if __name__ == "__main__":
    asyncio.run(main())
