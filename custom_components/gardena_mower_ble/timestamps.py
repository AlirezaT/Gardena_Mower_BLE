"""Decode mower local-wall-clock timestamps without guessing DST folds."""

from datetime import UTC, datetime


def local_timestamp(value, timezone):
    """Return a unique valid instant, or unknown for invalid/gap/fold values."""
    if type(value) is not int or not 0 < value < 0xFFFFFFFF or timezone is None:
        return None
    try:
        wall = datetime.fromtimestamp(value, UTC).replace(tzinfo=None)
        candidates = {}
        for fold in (0, 1):
            candidate = wall.replace(tzinfo=timezone, fold=fold)
            utc = candidate.astimezone(UTC)
            if utc.astimezone(timezone).replace(tzinfo=None) == wall:
                candidates[utc] = candidate
        return next(iter(candidates.values())) if len(candidates) == 1 else None
    except (ValueError, OverflowError, OSError):
        return None
