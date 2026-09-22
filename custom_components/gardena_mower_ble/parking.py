"""Local Return Home preferences; changing them never sends a mower command."""

import math

INDEFINITE = "Until further notice"
TIMED = "For a duration"
NEXT_SCHEDULE = "Until next schedule"
PARKING_OPTIONS = {0: INDEFINITE, 1: TIMED, 2: NEXT_SCHEDULE}
CONF_PARKING_MODE = "parking_mode"
CONF_PARKING_DURATION = "parking_duration_hours"


def validate_parking_duration(value):
    if isinstance(value, bool):
        raise ValueError("Parking duration must be 0.5–24 hours in half-hour steps")
    value = float(value)
    if not math.isfinite(value) or not 0.5 <= value <= 24 or value * 2 % 1:
        raise ValueError("Parking duration must be 0.5–24 hours in half-hour steps")
    return value


def saved_parking(options):
    mode = options.get(CONF_PARKING_MODE, INDEFINITE)
    if mode not in PARKING_OPTIONS.values():
        mode = INDEFINITE
    try:
        duration = validate_parking_duration(options.get(CONF_PARKING_DURATION, 3))
    except (TypeError, ValueError):
        duration = 3.0
    return mode, duration
