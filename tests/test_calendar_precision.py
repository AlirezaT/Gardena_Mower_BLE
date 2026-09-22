"""Exercise actual calendar methods with HA stand-ins, including startup errors."""

import ast
import datetime as dt
import re
import unittest
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock

from automower_ble.protocol import TaskInformation
from test_connection import Mower  # noqa: F401 - establishes lightweight integration package
from test_release_fixes import COMPONENT
from gardena_connection_tests.schedule import SecondTask, task_seconds


class Base:
    def __init__(self, coordinator):
        self.coordinator = coordinator

    @property
    def available(self):
        return True


@dataclass
class Event:
    start: dt.datetime
    end: dt.datetime
    summary: str
    description: str
    uid: str
    recurrence_id: str
    rrule: str

    @property
    def start_datetime_local(self):
        return self.start

    @property
    def end_datetime_local(self):
        return self.end


def calendar_class():
    tree = ast.parse((COMPONENT / "calendar.py").read_text())
    tree.body = [n for n in tree.body if isinstance(n, (ast.Assign, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) or isinstance(n, ast.ImportFrom) and n.module == "__future__"]
    namespace = {
        "dt": dt, "re": re, "TaskInformation": TaskInformation,
        "SecondTask": SecondTask, "task_seconds": task_seconds,
        "GardenaMowerBleEntity": Base, "CalendarEntity": object,
        "CalendarEvent": Event, "HomeAssistantError": RuntimeError,
        "CalendarEntityFeature": SimpleNamespace(CREATE_EVENT=1, DELETE_EVENT=2, UPDATE_EVENT=4),
        "dt_util": SimpleNamespace(
            now=lambda: dt.datetime(2026, 9, 23, 12, tzinfo=dt.UTC),
            as_local=lambda t: t, parse_datetime=dt.datetime.fromisoformat,
            start_of_local_day=lambda t: t.replace(tzinfo=dt.UTC),
        ),
    }
    exec(compile(tree, "calendar.py", "exec"), namespace)
    return namespace["GardenaMowerScheduleCalendar"]


class CalendarPrecisionTests(unittest.IsolatedAsyncioTestCase):
    def calendar(self):
        task = SecondTask(59555, 3617, False, False, True, False, False, False, False)
        mower = SimpleNamespace(is_connected=lambda: True, get_tasks=AsyncMock(return_value=[task]))
        coordinator = SimpleNamespace(mower=mower, address="test", channel_id=1)
        return calendar_class()(coordinator), task

    async def test_failed_initial_read_does_not_prevent_registration_and_recovers(self):
        calendar, task = self.calendar()
        reader = calendar.coordinator.mower.get_tasks
        reader.side_effect = RuntimeError("unavailable")
        await calendar.async_update()
        self.assertFalse(calendar.available)
        self.assertIsNone(calendar.extra_state_attributes["schedule_count"])
        self.assertTrue(calendar.should_poll)
        reader.side_effect = None
        await calendar.async_update()
        self.assertTrue(calendar.available)
        self.assertEqual(calendar._tasks, [task])
        reader.side_effect = RuntimeError("unavailable")
        await calendar.async_update()
        self.assertFalse(calendar.available)
        self.assertEqual(calendar._tasks, [task])
        with self.assertRaises(RuntimeError):
            await calendar._async_get_tasks()  # edits must not use stale snapshot

    async def test_display_and_event_expansion_keep_seconds(self):
        calendar, task = self.calendar()
        await calendar.async_update()
        attributes = calendar.extra_state_attributes
        self.assertIn("16:32:35-17:32:52", attributes["schedules"][0])
        self.assertEqual(attributes["raw_schedules"][0]["start"], 59555)
        event = calendar.event
        self.assertEqual(event.start.time(), dt.time(16, 32, 35))
        self.assertEqual((event.end - event.start).total_seconds(), 3617)
        rebuilt = calendar._task_from_event({"start": event.start, "end": event.end})
        self.assertEqual(task_seconds(rebuilt), task_seconds(task))
        partial = calendar._task_from_event({"summary": "unchanged"}, fallback=task)
        self.assertEqual(task_seconds(partial), task_seconds(task))

    async def test_recurrence_delete_matches_exact_seconds(self):
        calendar, task = self.calendar()
        other = SecondTask(59556, 3617, False, False, True, False, False, False, False)
        index = calendar._task_index_from_delete_request("foreign-id", "2026-09-23T16:32:36+00:00", [task, other])
        self.assertEqual(index, 1)
