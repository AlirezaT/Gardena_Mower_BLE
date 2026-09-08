"""Regression tests for issue 12 persistence and issue 11 start recovery."""

import ast
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from automower_ble.protocol import MowerActivity, MowerState, ResponseResult
from bleak import BleakError

COMPONENT = Path(__file__).parents[1] / "custom_components/gardena_mower_ble"


def load(name):
    spec = importlib.util.spec_from_file_location(name, COMPONENT / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DURATION = load("duration")
CONTROL = load("control")


def method(filename, class_name, name, namespace):
    """Run the actual HA-facing method with lightweight collaborator fakes."""
    tree = ast.parse((COMPONENT / filename).read_text())
    cls = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    node = next(
        node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), filename, "exec"), namespace)
    return namespace[name]


class DurationTests(unittest.TestCase):
    def test_persist_and_restore_across_new_coordinator(self):
        entry = SimpleNamespace(options={"unrelated": True})

        def update(target, *, options):
            target.options = options

        coordinator = SimpleNamespace(
            config_entry=entry,
            hass=SimpleNamespace(
                config_entries=SimpleNamespace(async_update_entry=update)
            ),
            update_cached_data=Mock(),
        )
        setter = method(
            "coordinator.py",
            "GardenaCoordinator",
            "set_manual_mowing_duration",
            vars(DURATION).copy(),
        )
        for value in (6.0, 0.5, 1.5, 24.0):
            setter(coordinator, value)
            self.assertEqual(DURATION.saved_duration(entry.options), value)
            self.assertEqual(coordinator.manual_mowing_duration_hours, value)
            coordinator.update_cached_data.assert_called_with(
                {"ManualMowingDuration": value}
            )
            self.assertTrue(entry.options["unrelated"])

    def test_invalid_stored_values_fall_back(self):
        for value in (None, "unavailable", float("nan"), float("inf"), 0, 25, 1.25):
            self.assertEqual(
                DURATION.saved_duration({DURATION.CONF_MANUAL_MOWING_DURATION: value}),
                3.0,
            )

    def test_half_hours_are_not_truncated_by_number(self):
        getter = method("number.py", "GardenaMowerBleNumber", "native_value", {})
        entity = SimpleNamespace(
            coordinator=SimpleNamespace(data={"ManualMowingDuration": 1.5}),
            entity_description=SimpleNamespace(key="ManualMowingDuration", scale=1),
        )
        self.assertEqual(getter(entity), 1.5)


class RestoreTests(unittest.IsolatedAsyncioTestCase):
    def entity(self, options, number=None, state=None):
        class NumberBase:
            async def async_added_to_hass(self):
                pass

        class RestoreBase:
            pass

        tree = ast.parse((COMPONENT / "number.py").read_text())
        cls = next(
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "GardenaMowerBleManualDuration"
        )
        namespace = dict(
            vars(DURATION), GardenaMowerBleNumber=NumberBase, RestoreNumber=RestoreBase
        )
        exec(
            compile(ast.Module(body=[cls], type_ignores=[]), "number.py", "exec"),
            namespace,
        )
        entity = namespace[cls.name]()
        entity.coordinator = SimpleNamespace(
            config_entry=SimpleNamespace(options=options),
            set_manual_mowing_duration=Mock(),
        )
        entity.async_get_last_number_data = AsyncMock(return_value=number)
        entity.async_get_last_state = AsyncMock(return_value=state)
        return entity

    async def test_options_take_precedence_over_stale_restore(self):
        entity = self.entity(
            {DURATION.CONF_MANUAL_MOWING_DURATION: 6.0},
            SimpleNamespace(native_value=3.0),
        )
        await entity.async_added_to_hass()
        entity.async_get_last_number_data.assert_not_called()
        entity.coordinator.set_manual_mowing_duration.assert_not_called()

    async def test_restore_number_data(self):
        entity = self.entity({}, SimpleNamespace(native_value=1.5))
        await entity.async_added_to_hass()
        entity.coordinator.set_manual_mowing_duration.assert_called_once_with(1.5)

    async def test_migrate_previous_plain_number_state(self):
        entity = self.entity({}, state=SimpleNamespace(state="6.0"))
        await entity.async_added_to_hass()
        entity.coordinator.set_manual_mowing_duration.assert_called_once_with(6.0)

    async def test_invalid_restore_is_ignored(self):
        entity = self.entity({}, state=SimpleNamespace(state="unavailable"))
        await entity.async_added_to_hass()
        entity.coordinator.set_manual_mowing_duration.assert_not_called()


class StartTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mower = SimpleNamespace(
            mower_state=AsyncMock(return_value=MowerState.RESTRICTED),
            mower_activity=AsyncMock(return_value=MowerActivity.PARKED),
            mower_override=AsyncMock(return_value=ResponseResult.OK),
            disconnect=AsyncMock(),
        )
        self.ensure = AsyncMock()

    async def start(self):
        await CONTROL.start_manual_mowing(self.mower, 1.5, self.ensure)

    async def test_success_uses_selected_duration(self):
        await self.start()
        self.mower.mower_override.assert_awaited_once_with(1.5)
        self.mower.disconnect.assert_not_called()

    async def test_transient_restart_failure_reconnects_once(self):
        self.mower.mower_override.side_effect = [
            ResponseResult.UNKNOWN_ERROR,
            ResponseResult.OK,
        ]
        await self.start()
        self.assertEqual(self.ensure.await_count, 2)
        self.mower.disconnect.assert_awaited_once()
        self.assertEqual(self.mower.mower_override.await_count, 2)

    async def test_accepted_start_is_not_replayed(self):
        self.mower.mower_override.return_value = ResponseResult.UNKNOWN_ERROR
        self.mower.mower_state.side_effect = [
            MowerState.RESTRICTED,
            MowerState.PENDING_START,
        ]
        await self.start()
        self.mower.mower_override.assert_awaited_once()

    async def test_physical_stop_is_never_bypassed(self):
        self.mower.mower_state.return_value = MowerState.STOPPED
        with self.assertRaisesRegex(CONTROL.ManualStartError, "STOPPED"):
            await self.start()
        self.mower.mower_override.assert_not_called()

    async def test_unknown_state_does_not_allow_start(self):
        self.mower.mower_state.return_value = None
        with self.assertRaises(CONTROL.ManualStartError):
            await self.start()
        self.mower.mower_override.assert_not_called()

    async def test_pending_without_activity_is_not_accepted(self):
        self.mower.mower_override.return_value = ResponseResult.UNKNOWN_ERROR
        self.mower.mower_state.side_effect = [
            MowerState.RESTRICTED,
            MowerState.PENDING_START,
        ]
        self.mower.mower_activity.side_effect = [
            MowerActivity.PARKED,
            MowerActivity.NONE,
        ]
        with self.assertRaisesRegex(CONTROL.ManualStartError, "safety/PIN"):
            await self.start()
        self.mower.mower_override.assert_awaited_once()

    async def test_permanent_failure_has_state_diagnostics(self):
        self.mower.mower_override.return_value = ResponseResult.NOT_ALLOWED
        with self.assertRaisesRegex(
            CONTROL.ManualStartError, "NOT_ALLOWED; state=RESTRICTED"
        ):
            await self.start()
        self.mower.mower_override.assert_awaited_once()

    async def test_transport_failure_rechecks_acceptance(self):
        self.mower.mower_override.side_effect = [
            BleakError("lost response"),
            ResponseResult.OK,
        ]
        self.mower.mower_state.side_effect = [
            MowerState.RESTRICTED,
            MowerState.IN_OPERATION,
        ]
        self.mower.mower_activity.side_effect = [
            MowerActivity.PARKED,
            MowerActivity.MOWING,
        ]
        await self.start()
        self.mower.mower_override.assert_awaited_once()

    async def test_repeat_failure_is_bounded(self):
        self.mower.mower_override.return_value = ResponseResult.UNKNOWN_ERROR
        with self.assertRaises(CONTROL.ManualStartError):
            await self.start()
        self.assertEqual(self.mower.mower_override.await_count, 2)


if __name__ == "__main__":
    unittest.main()
