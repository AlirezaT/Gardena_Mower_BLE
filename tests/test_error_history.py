"""Robot history reads: limits, failures, cancellation and HA response wiring."""

import asyncio
import ast
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

from test_connection import Mower
from automower_ble.protocol import ResponseResult as R
from gardena_connection_tests.error_history import (
    read_error_history,
    history_attributes,
    history_signature,
)
from test_release_fixes import method
from unittest.mock import Mock
from datetime import datetime, UTC


class HistoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_coordinator_cache_refresh_rotation_and_failure(self):
        entry = {"time": 100, "code": 2, "severity": 2}
        snapshot = {"total_messages": 1, "entries": [entry]}
        reader = AsyncMock(return_value=snapshot)
        update = method(
            "coordinator.py",
            "GardenaCoordinator",
            "_async_update_error_history",
            {
                "read_error_history": reader,
                "history_signature": history_signature,
                "dt_util": SimpleNamespace(
                    get_time_zone=ZoneInfo,
                    utcnow=lambda: datetime(2026, 9, 17, tzinfo=UTC),
                ),
                "BleakError": OSError,
                "LOGGER": Mock(),
            },
        )
        coordinator = SimpleNamespace(
            mower="mower",
            hass=SimpleNamespace(config=SimpleNamespace(time_zone="Europe/Brussels")),
        )
        data = {"NumberOfMessages": 1, "errorCode": 0}
        await update(coordinator, data, entry)
        self.assertEqual(data["error_history_status"], "ready")
        self.assertEqual(data["errorCode"], 0)
        await update(coordinator, data, entry)
        self.assertEqual(reader.await_count, 1)
        # Same count, different head: ring buffer rotated.
        rotated = {**entry, "time": 101}
        reader.return_value = {"total_messages": 1, "entries": [rotated]}
        await update(coordinator, data, rotated)
        self.assertEqual(reader.await_count, 2)
        reader.side_effect = RuntimeError("busy")
        await update(coordinator, data, entry)
        self.assertEqual(data["error_history_status"], "stale")
        self.assertEqual(data["error_history_snapshot"]["entries"], [rotated])
        # Failed fetch retries even if head/count now match the cached snapshot.
        reader.side_effect = None
        await update(coordinator, data, rotated)
        self.assertEqual(data["error_history_status"], "ready")
        self.assertEqual(reader.await_count, 4)
        # Genuine empty log clears previous entries.
        data["NumberOfMessages"] = 0
        reader.return_value = {"total_messages": 0, "entries": []}
        await update(coordinator, data, None)
        self.assertEqual(history_attributes(data)["error_history"], [])

    async def test_error_entity_keeps_state_and_adds_history(self):
        from gardena_connection_tests.presentation import describe_error
        from gardena_connection_tests.error_help import error_guidance

        mower = self.mower()
        data = {
            "errorCode": 0,
            "error_history_snapshot": {
                "total_messages": 1,
                "entries": [{"code": 2, "description": "Old error", "time": 100}],
            },
            "error_history_status": "ready",
        }
        entity = SimpleNamespace(
            coordinator=SimpleNamespace(data=data, capabilities=mower.capabilities),
            entity_description=SimpleNamespace(key="errorDescription"),
        )
        namespace = {
            "describe_error": describe_error,
            "history_attributes": history_attributes,
            "error_guidance": error_guidance,
        }
        value = method(
            "sensor.py", "GardenaMowerBleSensor", "native_value", namespace.copy()
        )
        attributes = method(
            "sensor.py",
            "GardenaMowerBleSensor",
            "extra_state_attributes",
            namespace.copy(),
        )
        self.assertEqual(value(entity), "No error")
        self.assertEqual(attributes(entity)["error_history"][0]["code"], 2)
        self.assertEqual(attributes(entity)["reason"], "No error")
        entity.entity_description.key = "errorCode"
        self.assertEqual(value(entity), 0)
        self.assertEqual(attributes(entity)["latest_stored_message"]["time"], 100)
        self.assertEqual(history_attributes({})["error_history_status"], "not_loaded")

    def mower(self, count=3):
        mower = Mower(1, "00:00:00:00:00:00")

        async def command(name, **kwargs):
            if name == "GetNumberOfMessages":
                return R.OK, count
            self.assertEqual(name, "GetMessage")  # Never sends a write.
            return R.OK, {
                "time": 1700000000,
                "code": kwargs["messageId"] + 1,
                "severity": 2,
            }

        mower.command_response = AsyncMock(side_effect=command)
        return mower

    async def test_page_preserves_raw_fields_and_formats_display(self):
        mower = self.mower()
        result = await read_error_history(
            mower, max_entries=2, timezone=ZoneInfo("Europe/Brussels")
        )
        self.assertEqual(result["source"], "robot")
        self.assertEqual(result["returned"], 2)
        self.assertEqual(result["next_offset"], 2)
        self.assertEqual([x["index"] for x in result["entries"]], [0, 1])
        self.assertEqual(result["entries"][0]["time"], 1700000000)
        self.assertEqual(result["entries"][0]["severity_name"], "error")
        self.assertIn("app_time_24h", result["entries"][0])
        json.dumps(result)
        page = await read_error_history(mower, offset=2)
        self.assertEqual(page["returned"], 1)
        self.assertIsNone(page["next_offset"])

    async def test_empty_is_valid_and_does_not_read_message(self):
        mower = self.mower(0)
        result = await read_error_history(mower)
        self.assertEqual(result["entries"], [])
        self.assertTrue(
            all(
                c.args[0] == "GetNumberOfMessages"
                for c in mower.command_response.await_args_list
            )
        )

    async def test_limits_and_offset(self):
        mower = self.mower(1000)
        result = await read_error_history(mower, max_entries=50, offset=49)
        self.assertEqual(result["total_messages"], 1000)
        self.assertEqual(result["available_messages"], 50)
        self.assertEqual(result["returned"], 1)
        self.assertIsNone(result["next_offset"])
        for kwargs in (
            {"max_entries": 0},
            {"max_entries": 51},
            {"max_entries": True},
            {"offset": -1},
            {"offset": 50},
        ):
            mower.command_response.reset_mock()
            with self.assertRaises(ValueError):
                await read_error_history(mower, **kwargs)
            mower.command_response.assert_not_awaited()

    async def test_failure_is_not_empty_or_partial_success(self):
        for result in (R.NOT_AVAILABLE, R.DEVICE_BUSY, R.UNKNOWN_ERROR, R.INVALID_ID):
            mower = self.mower()
            mower.command_response.side_effect = [(result, None)]
            with self.assertRaises(RuntimeError):
                await read_error_history(mower)
        mower = self.mower()
        mower.command_response.side_effect = [
            (R.OK, 2),
            (R.OK, {"time": 0, "code": 1, "severity": 2}),
            (R.INVALID_ID, None),
        ]
        with self.assertRaises(RuntimeError):
            await read_error_history(mower)

    async def test_invalid_counts_and_entries(self):
        for count in (None, True, -1, 0xFFFFFFFF, "3"):
            with self.assertRaises(ValueError):
                await read_error_history(self.mower(count))
        for entry in (
            None,
            {},
            {"time": 0, "code": True, "severity": 2},
            {"time": -1, "code": 1, "severity": 2},
        ):
            mower = self.mower()
            mower.command_response.side_effect = [(R.OK, 1), (R.OK, entry)]
            with self.assertRaises(ValueError):
                await read_error_history(mower)

    async def test_unknown_codes_and_invalid_clock_are_not_discarded(self):
        mower = self.mower()
        entry = {"time": 0xFFFFFFFF, "code": 99999, "severity": 255}
        mower.command_response.side_effect = [
            (R.OK, 1),
            (R.OK, entry),
            (R.OK, 1),
            (R.OK, entry),
        ]
        result = await read_error_history(mower)
        self.assertEqual(result["entries"][0]["description"], "Unknown error (99999)")
        self.assertEqual(result["entries"][0]["severity"], 255)
        self.assertNotIn("app_date", result["entries"][0])

    async def test_detects_count_change_and_same_size_rotation(self):
        entry = {"time": 1, "code": 2, "severity": 2}
        for replies in (
            [(R.OK, 1), (R.OK, entry), (R.OK, 2)],
            [(R.OK, 1), (R.OK, entry), (R.OK, 1), (R.OK, {**entry, "code": 3})],
        ):
            mower = self.mower()
            mower.command_response.side_effect = replies
            with self.assertRaisesRegex(RuntimeError, "changed"):
                await read_error_history(mower)

    async def test_cancellation_releases_lock(self):
        mower = self.mower()
        mower.command_response.side_effect = asyncio.CancelledError
        with self.assertRaises(asyncio.CancelledError):
            await read_error_history(mower)
        self.assertFalse(mower.lock.locked())

    async def test_service_registration_and_response(self):
        # Execute the actual HA registration function using lightweight HA fakes.
        import voluptuous as vol

        source = (
            Path(__file__).parents[1]
            / "custom_components/gardena_mower_ble/__init__.py"
        )
        tree = ast.parse(source.read_text())
        node = next(
            n
            for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "_async_register_services"
        )
        registrations = {}
        hass = SimpleNamespace(
            config=SimpleNamespace(time_zone="Europe/Brussels"),
            services=SimpleNamespace(
                has_service=lambda domain, name: name != "get_error_history",
                async_register=lambda domain,
                name,
                handler,
                **kwargs: registrations.update({name: (handler, kwargs)}),
            ),
        )
        reader = AsyncMock(return_value={"source": "robot", "entries": []})
        namespace = {
            "HomeAssistant": object,
            "ServiceCall": object,
            "HomeAssistantError": RuntimeError,
            "SupportsResponse": SimpleNamespace(ONLY="only"),
            "DOMAIN": "gardena_mower_ble",
            "vol": vol,
            "dt_util": SimpleNamespace(get_time_zone=ZoneInfo),
            "read_error_history": reader,
            "BleakError": OSError,
            "_async_get_service_coordinator": AsyncMock(
                return_value=SimpleNamespace(mower="mower")
            ),
        }
        for name in (
            "GET_ERROR_HISTORY",
            "LOG_ERROR_HISTORY",
            "DELETE_SCHEDULE",
            "CLEAR_SCHEDULE",
            "REFRESH_DIAGNOSTICS",
        ):
            namespace["SERVICE_" + name] = name.lower()
        exec(
            compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"),
            namespace,
        )
        namespace["_async_register_services"](hass)
        handler, options = registrations["get_error_history"]
        self.assertEqual(options["supports_response"], "only")
        data = options["schema"]({})
        self.assertEqual(data, {"offset": 0, "max_entries": 10})
        self.assertEqual(
            await handler(SimpleNamespace(data=data)),
            {"source": "robot", "entries": []},
        )
        reader.side_effect = ValueError("bad response")
        with self.assertRaisesRegex(RuntimeError, "Unable to read"):
            await handler(SimpleNamespace(data=data))

    async def test_timeout_releases_lock(self):
        mower = self.mower()

        async def wait(*args, **kwargs):
            await asyncio.Event().wait()

        mower.command_response.side_effect = wait
        timeout = asyncio.timeout
        with patch(
            "gardena_connection_tests.error_history.asyncio.timeout",
            side_effect=lambda seconds: timeout(0.01),
        ):
            with self.assertRaises(TimeoutError):
                await read_error_history(mower)
        self.assertFalse(mower.lock.locked())

    async def test_history_does_not_interleave_with_other_transactions(self):
        mower = self.mower()
        async with mower.lock:
            task = asyncio.create_task(read_error_history(mower))
            await asyncio.sleep(0)
            mower.command_response.assert_not_awaited()
        result = await task
        self.assertEqual(result["returned"], 3)
