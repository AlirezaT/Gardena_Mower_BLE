"""Render actual window templates and exercise the guard's action branches."""

import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import test_mowing_budget as budget
from jinja2.nativetypes import NativeEnvironment

BLUEPRINT = budget.BLUEPRINT


class WindowTests(unittest.TestCase):
    def evaluate(self, clock="2026-10-15T00:00:00", **overrides):
        now = datetime.fromisoformat(clock).replace(tzinfo=ZoneInfo("Europe/Brussels"))
        values = {k: v.get("default") for k, v in BLUEPRINT["blueprint"]["input"].items()}
        values.update(
            mower_entity="lawn_mower.test",
            permanent_park_switch="switch.park",
            allowed_start_reference="Sunrise",
            allowed_start_sun_offset_minutes=300,
            allowed_end_reference="Sunset",
            allowed_end_sun_offset_minutes=-30,
            trigger={"id": "window_guard"},
        )
        states = {"lawn_mower.test": "mowing", "switch.park": "off"}
        states.update(overrides.pop("states", {}))
        values.update(overrides)
        env = NativeEnvironment()
        env.filters["bool"] = lambda v: str(v).lower() in ("true", "1", "on", "yes")

        def today_at(t):
            return datetime.combine(now.date(), datetime.strptime(t, "%H:%M:%S").time(), now.tzinfo)

        def sun_attr(entity, attr):
            event = today_at("08:02:28" if attr == "next_rising" else "18:47:08")
            return event if event > now else event + timedelta(days=1)

        env.globals.update(
            now=lambda: now, today_at=today_at, timedelta=timedelta,
            as_timestamp=lambda t, default=None: t.timestamp() if t is not None else default,
            state_attr=sun_attr, states=lambda e: states.get(e, "unknown"),
            is_state=lambda e, s: states.get(e) == s,
        )
        render = lambda t: budget.BudgetTests.render(env.from_string(t), values)
        # This is the first action, deliberately refreshing queued-run variables.
        for name, template in BLUEPRINT["action"][0]["variables"].items():
            values[name] = render(template)
        return values, render

    def guard_calls(self, **overrides):
        values, render = self.evaluate(**overrides)
        calls = []

        def walk(actions):
            for action in actions:
                if "choose" in action:
                    for branch in action["choose"]:
                        if render(branch["conditions"]):
                            walk(branch["sequence"])
                            break
                    else:
                        walk(action.get("default", []))
                elif "action" in action:
                    calls.append(action["action"])
                else:
                    self.fail(f"Unexpected guard action: {action}")

        walk([BLUEPRINT["action"][1]])
        return calls

    def test_midnight_scheduled_start_is_parked_indefinitely(self):
        self.assertEqual(self.guard_calls(), ["switch.turn_on"])

    def test_docked_mower_is_held_before_it_can_resume(self):
        self.assertEqual(self.guard_calls(states={"lawn_mower.test": "docked"}), ["switch.turn_on"])

    def test_existing_hold_is_not_repeated(self):
        self.assertEqual(self.guard_calls(states={"switch.park": "on"}), [])

    def test_unknown_hold_is_not_assumed_enabled(self):
        self.assertEqual(self.guard_calls(states={"switch.park": "unknown"}), ["switch.turn_on"])

    def test_unavailable_mower_is_not_commanded(self):
        self.assertEqual(self.guard_calls(states={"lawn_mower.test": "unavailable"}), [])

    def test_allowed_afternoon_is_not_parked(self):
        self.assertEqual(self.guard_calls(clock="2026-10-15T14:00:00"), [])

    def test_excluded_weekday_is_parked_even_in_afternoon(self):
        self.assertEqual(self.guard_calls(clock="2026-10-15T14:00:00", excluded_mowing_weekdays=["Thursday"]), ["switch.turn_on"])

    def test_opt_out_preserves_start_only_window(self):
        self.assertEqual(self.guard_calls(enforce_mowing_window=False), [])

    def test_generic_fallback_only_docks_when_mowing(self):
        self.assertEqual(self.guard_calls(permanent_park_switch=""), ["lawn_mower.dock"])
        self.assertEqual(self.guard_calls(permanent_park_switch="", states={"lawn_mower.test": "docked"}), [])

    def test_end_boundary_is_exclusive(self):
        self.assertEqual(self.guard_calls(clock="2026-10-15T18:17:08"), ["switch.turn_on"])
        self.assertEqual(self.guard_calls(clock="2026-10-15T18:17:07"), [])

    def test_start_boundary_is_inclusive(self):
        self.assertEqual(self.guard_calls(clock="2026-10-15T13:02:28"), [])
        self.assertEqual(self.guard_calls(clock="2026-10-15T13:02:27"), ["switch.turn_on"])

    def test_solar_offsets_that_close_window_do_not_enable_night_mowing(self):
        for hour in [0, 14, 23]:
            values, _ = self.evaluate(clock=f"2026-10-15T{hour:02}:00:00", allowed_start_sun_offset_minutes=720)
            self.assertFalse(values["within_allowed_time"])

    def test_explicit_fixed_overnight_window_still_works(self):
        for hour, expected in [(0, True), (5, True), (6, False), (12, False), (22, True)]:
            values, _ = self.evaluate(clock=f"2026-10-15T{hour:02}:00:00", allowed_start_reference="Fixed time", allowed_end_reference="Fixed time", allowed_start_time="22:00:00", allowed_end_time="06:00:00")
            self.assertEqual(values["within_allowed_time"], expected)

    def test_equal_boundaries_are_closed_not_all_day(self):
        values, _ = self.evaluate(allowed_start_reference="Fixed time", allowed_end_reference="Fixed time", allowed_start_time="00:00:00", allowed_end_time="00:00:00")
        self.assertFalse(values["within_allowed_time"])

    def test_guard_tick_stops_before_weather_or_start(self):
        _, render = self.evaluate()
        branch = BLUEPRINT["action"][2]["choose"][0]
        self.assertTrue(render(branch["conditions"]))
        self.assertIn("stop", branch["sequence"][0])
        for trigger in ["mowing_started", "schedule_check"]:
            _, render = self.evaluate(trigger={"id": trigger})
            self.assertFalse(render(branch["conditions"]))

    def test_refresh_before_start_and_on_execution(self):
        refresh = BLUEPRINT["action"][0]["variables"]
        actions = BLUEPRINT["action"]
        index = next(i for i, a in enumerate(actions) if a.get("condition") == "template" and "safe_to_mow" in a.get("value_template", ""))
        self.assertEqual(actions[index - 1]["variables"], refresh)
        self.assertIn("within_allowed_time", actions[index]["value_template"])
        self.assertIn("allowed_weekday_today", actions[index]["value_template"])

    def test_startup_and_minute_guard_triggers_exist(self):
        guards = [t for t in BLUEPRINT["trigger"] if t["id"] == "window_guard"]
        self.assertIn({"platform": "homeassistant", "event": "start", "id": "window_guard"}, guards)
        self.assertIn({"platform": "time_pattern", "minutes": "/1", "id": "window_guard"}, guards)


if __name__ == "__main__":
    unittest.main()
