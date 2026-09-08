"""Validation for the locally stored manual mowing duration."""

import math

CONF_MANUAL_MOWING_DURATION = "manual_mowing_duration_hours"
DEFAULT_MANUAL_MOWING_DURATION_HOURS = 3.0


def validate_duration(value):
    """Preserve half hours and reject invalid stored or requested values."""
    value = float(value)
    if not math.isfinite(value) or not 0.5 <= value <= 24 or value * 2 % 1:
        raise ValueError(
            "Manual mowing duration must be 0.5–24 hours in half-hour steps"
        )
    return value


def saved_duration(options):
    """Load a valid preference or use the first-install default."""
    try:
        return validate_duration(options[CONF_MANUAL_MOWING_DURATION])
    except (KeyError, TypeError, ValueError):
        return DEFAULT_MANUAL_MOWING_DURATION_HOURS
