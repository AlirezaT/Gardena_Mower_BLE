"""Regression tests rendering the blueprint's real budget and moisture templates."""

import ast
from datetime import datetime
from pathlib import Path
import unittest

from jinja2.nativetypes import NativeEnvironment
import yaml


class Loader(yaml.SafeLoader):
    pass


Loader.add_constructor("!input", lambda loader, node: loader.construct_scalar(node))
BLUEPRINT = yaml.load(
    (
        Path(__file__).parents[1] / "blueprints/automation/gardena_smart_mowing.yaml"
    ).read_text(),
    Loader=Loader,
)


class BudgetTests(unittest.TestCase):
    @staticmethod
    def render(template, values):
        result = template.render(**values)
        if isinstance(result, str):
            result = result.strip()
            try:
                return ast.literal_eval(result)
            except (ValueError, SyntaxError):
                pass
        return result

    def evaluate(self, **overrides):
        values = {
            key: entry.get("default")
            for key, entry in BLUEPRINT["blueprint"]["input"].items()
        }
        values.update(
            lawn_area_m2=140,
            mower_capacity_m2_per_hour=45,
            weekly_coverage_multiplier=1,
            min_sessions_per_week=5,
            max_sessions_per_week=7,
            min_session_minutes=60,
            grass_climate_type="Warm-season",
            growth_adjustment_percent=200,
            lawn_exposure="Sunny/open",
            outdoor_temperature=20,
            outdoor_humidity=50,
            last_rain_age_hours=100,
            water_lookback_days=7,
            weekly_water_target_mm=20,
            recent_rainfall_sensor="sensor.rain",
            recent_irrigation_sensor="sensor.water",
            irrigation_active_entities=["select.irrigation"],
            soil_moisture_sensor="",
        )
        states = {
            "sensor.rain": "2.95",
            "sensor.water": "unavailable",
            "select.irrigation": "unavailable",
        }
        states.update(overrides.pop("states", {}))
        values.update(overrides)
        env = NativeEnvironment()
        env.filters["bool"] = lambda value: (
            str(value).strip().lower() in ("true", "1", "on", "yes")
        )
        env.globals.update(
            states=lambda entity: states.get(entity, "unknown"),
            state_attr=lambda entity, attr: "mm" if entity == "sensor.rain" else "L",
            is_number=lambda value: str(value).replace(".", "", 1).isdigit(),
            now=lambda: datetime(2026, 9, 8, 12),
        )
        first = "base_weekly_minutes_needed"
        last = "daily_mowing_minutes_needed"
        enabled = False
        for name, template in BLUEPRINT["variables"].items():
            if name == first:
                enabled = True
            if enabled or name in [
                "irrigation_active",
                "irrigation_status_unavailable",
            ]:
                values[name] = self.render(env.from_string(template), values)
            if name == last:
                break
        return values, env

    def test_minimum_frequency_and_length_set_weekly_floor(self):
        result, _ = self.evaluate(states={"sensor.water": "0"})
        self.assertLess(result["growth_weekly_minutes_needed"], 300)
        self.assertEqual(result["weekly_minutes_needed"], 300)
        self.assertEqual(result["calculated_sessions_per_week"], 5)
        self.assertEqual(result["calculated_session_minutes"], 60)
        self.assertAlmostEqual(result["daily_mowing_minutes_needed"], 300 / 7, places=3)

    def test_missing_irrigation_is_not_zero_water(self):
        result, _ = self.evaluate()
        self.assertTrue(result["water_totals_incomplete"])
        self.assertFalse(result["use_water_totals_for_growth"])
        self.assertEqual(
            result["moisture_growth_factor"], result["legacy_moisture_growth_factor"]
        )
        self.assertFalse(result["irrigation_active"])
        self.assertTrue(result["irrigation_status_unavailable"])

    def test_real_zero_water_keeps_drought_adjustment(self):
        result, _ = self.evaluate(states={"sensor.water": "0", "sensor.rain": "0"})
        self.assertFalse(result["water_totals_incomplete"])
        self.assertEqual(result["moisture_growth_factor"], 0.4)

    def test_soil_is_used_when_configured_totals_are_incomplete(self):
        result, _ = self.evaluate(
            soil_moisture_sensor="sensor.soil", states={"sensor.soil": "50"}
        )
        self.assertEqual(result["moisture_growth_factor"], 1.0)

    def test_unconfigured_irrigation_does_not_invalidate_rain(self):
        result, _ = self.evaluate(recent_irrigation_sensor="")
        self.assertFalse(result["water_totals_incomplete"])
        self.assertTrue(result["use_water_totals_for_growth"])

    def test_lookback_uses_same_period_as_totals(self):
        seven, _ = self.evaluate()
        fourteen, _ = self.evaluate(water_lookback_days=14)
        self.assertAlmostEqual(seven["water_demand_mm"], 19.55)
        self.assertAlmostEqual(fourteen["water_demand_mm"], 39.1)

    def test_excluded_days_and_maximum_sessions_limit_floor(self):
        result, _ = self.evaluate(
            excluded_mowing_weekdays=[
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
            ],
            states={"sensor.water": "0", "sensor.rain": "0"},
        )
        self.assertEqual(result["effective_min_sessions"], 2)
        self.assertEqual(result["minimum_weekly_minutes_needed"], 120)
        capped, _ = self.evaluate(max_sessions_per_week=3)
        self.assertEqual(capped["effective_min_sessions"], 3)

    def test_active_irrigation_still_blocks(self):
        result, _ = self.evaluate(states={"select.irrigation": "watering"})
        self.assertTrue(result["irrigation_active"])
        self.assertFalse(result["irrigation_status_unavailable"])

    def test_quarter_hour_updates_preserve_daily_budget(self):
        result, env = self.evaluate()
        result.update(
            use_mowing_debt_helper=True,
            stored_mowing_debt_minutes=0,
            debt_elapsed_hours=0.25,
        )
        template = env.from_string(
            BLUEPRINT["variables"]["updated_mowing_debt_minutes"]
        )
        for _ in range(96):
            result["stored_mowing_debt_minutes"] = self.render(template, result)
        self.assertAlmostEqual(
            result["stored_mowing_debt_minutes"], 300 / 7, delta=0.05
        )


if __name__ == "__main__":
    unittest.main()
