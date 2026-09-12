"""Separate per-run budgets from persisted manual preferences."""

from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

from automower_ble.protocol import ModeOfOperation, MowerActivity, MowerState
from jinja2.nativetypes import NativeEnvironment

from test_mowing_budget import BLUEPRINT
from test_release_fixes import DURATION, method


class RunDurationTests(unittest.IsolatedAsyncioTestCase):
    async def test_automatic_and_manual_start_preserve_preference(self):
        for requested, expected in ((1.5, 1.5), (None, 3.0)):
            entry = SimpleNamespace(options={"manual_mowing_duration_hours": 3.0, "mower_brand": "gardena"})
            def update(entry, *, options):
                entry.options = options
            start = AsyncMock()
            coordinator = SimpleNamespace(
                config_entry=entry, manual_mowing_duration_hours=3.0,
                mower=object(), _async_find_device=AsyncMock(),
                hass=SimpleNamespace(config_entries=SimpleNamespace(async_update_entry=update)),
                update_cached_data=Mock(), schedule_action_refresh=Mock())
            entity = SimpleNamespace(coordinator=coordinator, _get_activity=Mock(), async_write_ha_state=Mock())
            fn = method("lawn_mower.py", "AutomowerLawnMower", "async_start_mowing", {
                "LOGGER": Mock(), "validate_duration": DURATION.validate_duration,
                "start_manual_mowing": start, "HomeAssistantError": RuntimeError,
                "MowerActivity": MowerActivity, "MowerState": MowerState, "ModeOfOperation": ModeOfOperation})
            await fn(entity, requested)
            self.assertEqual(start.await_args.args[1], expected)
            self.assertEqual(entry.options["manual_mowing_duration_hours"], 3.0)
            self.assertEqual(entry.options["last_start_duration_hours"], expected)
            self.assertEqual(entry.options["mower_brand"], "gardena")
            start.side_effect = RuntimeError("not accepted")
            before = dict(entry.options)
            with self.assertRaises(RuntimeError):
                await fn(entity, 2.0)
            self.assertEqual(entry.options, before)
            start.reset_mock()
            with self.assertRaises(RuntimeError):
                await fn(entity, 1.25)
            start.assert_not_awaited()

    def test_blueprint_service_branch_never_writes_manual_number(self):
        branch = next(step for step in BLUEPRINT["action"] if any(
            "start_mowing_for" in choice.get("conditions", "")
            for choice in step.get("choose", [])))
        self.assertEqual(branch["choose"][0]["sequence"][0]["action"], "gardena_mower_ble.start_mowing_for")
        self.assertEqual(len(branch["choose"][0]["sequence"]), 1)
        self.assertEqual([s["action"] for s in branch["default"]], ["number.set_value", "lawn_mower.start_mowing"])
        template = NativeEnvironment().from_string(branch["choose"][0]["conditions"])
        for service, ours, expected in ((True, True, True), (False, True, False), (True, False, False)):
            result = template.render(has_service=lambda *a: service,
                                     integration_entities=lambda *a: ["lawn_mower.test"] if ours else [],
                                     mower_entity="lawn_mower.test")
            self.assertEqual(result, expected)

    def test_accounting_uses_accepted_budget_not_manual_preference(self):
        templates = []
        def visit(node):
            if isinstance(node, dict):
                if "planned_minutes" in node:
                    templates.append(node["planned_minutes"])
                for value in node.values():
                    visit(value)
            elif isinstance(node, list):
                for value in node:
                    visit(value)
        visit(BLUEPRINT["action"])
        self.assertEqual(len(templates), 3)
        for source in templates:
            for saved, expected in ((1.5, 90), (None, 180)):
                result = NativeEnvironment().from_string(source).render(
                    state_attr=lambda *a: saved, states=lambda *a: "3.0",
                    mower_entity="lawn_mower.test", manual_duration_number="number.manual",
                    calculated_session_hours=2)
                self.assertEqual(result, expected)
