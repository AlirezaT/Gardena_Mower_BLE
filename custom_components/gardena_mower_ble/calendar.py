"""Support for Gardena mower schedule calendar entities."""

from __future__ import annotations

import datetime as dt
import math
import re
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
try:
    from homeassistant.components.calendar.const import CalendarEntityFeature
except ImportError:
    from homeassistant.components.calendar import CalendarEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import GardenaConfigEntry
from .automower_ble.mower import MAX_SCHEDULE_TASKS
from .automower_ble.protocol import TaskInformation
from .entity import GardenaMowerBleEntity

SUMMARY = "Mowing schedule"
UID_PREFIX = "gardena-mower-task-"

DAY_NAMES = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)
DAY_RRULE = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")
RRULE_DAY_TO_INDEX = {name: index for index, name in enumerate(DAY_RRULE)}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GardenaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Gardena mower calendar entities."""
    async_add_entities([GardenaMowerScheduleCalendar(entry.runtime_data)], True)


class GardenaMowerScheduleCalendar(GardenaMowerBleEntity, CalendarEntity):
    """Representation of the mower's weekly schedule as a calendar."""

    _attr_name = "Schedule"
    _attr_icon = "mdi:calendar-clock"
    _attr_supported_features = (
        CalendarEntityFeature.CREATE_EVENT
        | CalendarEntityFeature.DELETE_EVENT
        | CalendarEntityFeature.UPDATE_EVENT
    )

    def __init__(self, coordinator) -> None:
        """Initialize the schedule calendar."""
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.address}_{coordinator.channel_id}_schedule"
        )
        self._tasks: list[TaskInformation] = []

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next upcoming schedule event."""
        return self._next_event()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return schedule details as entity attributes."""
        next_event = self._next_event()
        return {
            "schedule_count": len(self._tasks),
            "next_start": (
                next_event.start_datetime_local.isoformat() if next_event else None
            ),
            "next_end": (
                next_event.end_datetime_local.isoformat() if next_event else None
            ),
            "schedules": [_task_description(task) for task in self._tasks],
        }

    def _next_event(self) -> CalendarEvent | None:
        """Return the current or next upcoming schedule event."""
        now = dt_util.now()
        events = self._expand_tasks(
            now - dt.timedelta(days=1), now + dt.timedelta(days=8)
        )
        current_or_next = [
            event for event in events if event.end_datetime_local > now
        ]
        return current_or_next[0] if current_or_next else None

    async def async_update(self) -> None:
        """Fetch schedule data from the mower."""
        self._tasks = await self._async_get_tasks()

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: dt.datetime,
        end_date: dt.datetime,
    ) -> list[CalendarEvent]:
        """Return schedule events within a datetime range."""
        self._tasks = await self._async_get_tasks()
        return self._expand_tasks(start_date, end_date)

    async def async_create_event(self, **kwargs: Any) -> None:
        """Add a new weekly mowing schedule."""
        tasks = await self._async_get_tasks()
        if len(tasks) >= MAX_SCHEDULE_TASKS:
            raise HomeAssistantError(
                f"The mower supports a maximum of {MAX_SCHEDULE_TASKS} schedules"
            )

        tasks.append(self._task_from_event(kwargs))
        await self._async_set_tasks(tasks)

    async def async_delete_event(
        self,
        uid: str,
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> None:
        """Delete a weekly mowing schedule."""
        tasks = await self._async_get_tasks()
        task_index = self._task_index_from_delete_request(uid, recurrence_id, tasks)
        if task_index >= len(tasks):
            raise HomeAssistantError(f"Schedule {task_index + 1} does not exist")

        del tasks[task_index]
        await self._async_set_tasks(tasks)

    async def async_update_event(
        self,
        uid: str,
        event: dict[str, Any],
        recurrence_id: str | None = None,
        recurrence_range: str | None = None,
    ) -> None:
        """Update a weekly mowing schedule."""
        task_index = self._task_index_from_uid(uid)
        tasks = await self._async_get_tasks()
        if task_index >= len(tasks):
            raise HomeAssistantError(f"Schedule {task_index + 1} does not exist")

        tasks[task_index] = self._task_from_event(event, fallback=tasks[task_index])
        await self._async_set_tasks(tasks)

    async def _async_get_tasks(self) -> list[TaskInformation]:
        """Fetch all tasks, reconnecting first if needed."""
        if not self.coordinator.mower.is_connected():
            await self.coordinator._async_find_device()

        try:
            return await self.coordinator.mower.get_tasks()
        except Exception as err:
            raise HomeAssistantError(f"Unable to read mower schedule: {err}") from err

    async def _async_set_tasks(self, tasks: list[TaskInformation]) -> None:
        """Write all tasks and refresh HA state."""
        if not self.coordinator.mower.is_connected():
            await self.coordinator._async_find_device()

        try:
            await self.coordinator.mower.set_tasks(tasks)
        except Exception as err:
            raise HomeAssistantError(f"Unable to update mower schedule: {err}") from err

        self._tasks = tasks
        self.async_write_ha_state()
        if update_event_listeners := getattr(
            self, "async_update_event_listeners", None
        ):
            result = update_event_listeners()
            if hasattr(result, "__await__"):
                await result
        await self.coordinator.async_request_refresh()

    def _expand_tasks(
        self, start_date: dt.datetime, end_date: dt.datetime
    ) -> list[CalendarEvent]:
        """Expand weekly mower tasks into concrete calendar events."""
        events: list[CalendarEvent] = []
        start_day = (start_date - dt.timedelta(days=1)).date()
        end_day = (end_date + dt.timedelta(days=1)).date()

        day = start_day
        while day <= end_day:
            weekday = day.weekday()
            for index, task in enumerate(self._tasks):
                if not _task_days(task)[weekday]:
                    continue

                event_start = _local_midnight(day) + dt.timedelta(
                    minutes=task.start_time_in_minutes
                )
                event_end = event_start + dt.timedelta(
                    minutes=task.duration_in_minutes
                )
                if event_end <= start_date or event_start >= end_date:
                    continue

                events.append(
                    CalendarEvent(
                        start=event_start,
                        end=event_end,
                        summary=SUMMARY,
                        description=_task_description(task),
                        uid=f"{UID_PREFIX}{index}",
                        recurrence_id=event_start.isoformat(),
                        rrule=_task_rrule(task),
                    )
                )
            day += dt.timedelta(days=1)

        return sorted(events, key=lambda event: event.start_datetime_local)

    def _task_from_event(
        self,
        event: dict[str, Any],
        fallback: TaskInformation | None = None,
    ) -> TaskInformation:
        """Convert a HA calendar event to a mower schedule task."""
        start = event.get("start")
        end = event.get("end")

        if start is None and fallback is not None:
            start_minutes = fallback.start_time_in_minutes
            duration_minutes = fallback.duration_in_minutes
            selected_days = _task_days(fallback)
        elif isinstance(start, dt.datetime) and isinstance(end, dt.datetime):
            start = dt_util.as_local(start)
            end = dt_util.as_local(end)
            start_minutes = start.hour * 60 + start.minute
            duration_minutes = math.ceil((end - start).total_seconds() / 60)
            selected_days = _days_from_rrule(event.get("rrule")) or [
                index == start.weekday() for index in range(7)
            ]
        else:
            raise HomeAssistantError("Mower schedules must use start and end date-times")

        if duration_minutes <= 0:
            raise HomeAssistantError("Schedule duration must be greater than zero")
        if duration_minutes > 24 * 60:
            raise HomeAssistantError("Schedule duration cannot be longer than 24 hours")

        return TaskInformation(
            start_minutes,
            duration_minutes,
            selected_days[0],
            selected_days[1],
            selected_days[2],
            selected_days[3],
            selected_days[4],
            selected_days[5],
            selected_days[6],
        )

    def _task_index_from_uid(self, uid: str) -> int:
        """Extract the mower task index from a calendar uid."""
        if not uid.startswith(UID_PREFIX):
            raise HomeAssistantError(f"Unknown mower schedule uid: {uid}")

        try:
            return int(uid.removeprefix(UID_PREFIX))
        except ValueError as err:
            raise HomeAssistantError(f"Unknown mower schedule uid: {uid}") from err

    def _task_index_from_delete_request(
        self,
        uid: str,
        recurrence_id: str | None,
        tasks: list[TaskInformation],
    ) -> int:
        """Extract or infer the task index from a calendar delete request."""
        try:
            return self._task_index_from_uid(uid)
        except HomeAssistantError:
            if recurrence_id is None:
                raise

        try:
            recurrence_start = dt_util.parse_datetime(recurrence_id)
        except (TypeError, ValueError) as err:
            raise HomeAssistantError(f"Unknown mower schedule uid: {uid}") from err

        if recurrence_start is None:
            raise HomeAssistantError(f"Unknown mower schedule uid: {uid}")

        recurrence_start = dt_util.as_local(recurrence_start)
        start_minutes = recurrence_start.hour * 60 + recurrence_start.minute
        weekday = recurrence_start.weekday()
        matches = [
            index
            for index, task in enumerate(tasks)
            if task.start_time_in_minutes == start_minutes and _task_days(task)[weekday]
        ]
        if len(matches) != 1:
            raise HomeAssistantError(f"Unknown mower schedule uid: {uid}")

        return matches[0]


def _local_midnight(day: dt.date) -> dt.datetime:
    """Return midnight for a local date."""
    return dt_util.start_of_local_day(dt.datetime.combine(day, dt.time.min))


def _task_days(task: TaskInformation) -> list[bool]:
    """Return the enabled weekdays, Monday first."""
    return [
        bool(task.on_monday),
        bool(task.on_tuesday),
        bool(task.on_wednesday),
        bool(task.on_thursday),
        bool(task.on_friday),
        bool(task.on_saturday),
        bool(task.on_sunday),
    ]


def _task_rrule(task: TaskInformation) -> str:
    """Return a weekly rrule for a mower task."""
    days = [
        day_name
        for day_name, enabled in zip(DAY_RRULE, _task_days(task), strict=True)
        if enabled
    ]
    return f"FREQ=WEEKLY;BYDAY={','.join(days)}"


def _task_description(task: TaskInformation) -> str:
    """Return a human-friendly task description."""
    start = _format_minutes(task.start_time_in_minutes)
    stop_time = task.start_time_in_minutes + task.duration_in_minutes
    end = _format_minutes(stop_time)
    if stop_time > 24 * 60:
        end = f"next day {end}"
    days = ", ".join(
        day_name.title()
        for day_name, enabled in zip(DAY_NAMES, _task_days(task), strict=True)
        if enabled
    )
    return f"{start}-{end} on {days}"


def _format_minutes(minutes: int) -> str:
    """Format minutes after midnight as HH:MM."""
    minutes = minutes % (24 * 60)
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _days_from_rrule(rrule: str | None) -> list[bool] | None:
    """Extract BYDAY weekdays from a simple weekly rrule."""
    if not rrule:
        return None

    match = re.search(r"(?:^|;)BYDAY=([^;]+)", rrule)
    if not match:
        return None

    selected = [False] * 7
    for value in match.group(1).split(","):
        if value in RRULE_DAY_TO_INDEX:
            selected[RRULE_DAY_TO_INDEX[value]] = True

    return selected if any(selected) else None
