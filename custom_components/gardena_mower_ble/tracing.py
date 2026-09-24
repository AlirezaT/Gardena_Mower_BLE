"""Local action correlation and response provenance without packet payloads."""

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
import logging

_LOGGER = logging.getLogger(__name__)
_ACTION = ContextVar("gardena_action", default=None)
REQUEST_TRACE = ContextVar("gardena_request_trace", default=None)


def action_id(mower):
    """Exclude other mowers and child tasks such as a persistent heartbeat."""
    current = _ACTION.get()
    if current is not None and current[0] is mower and current[2] is asyncio.current_task():
        return current[1]
    return "none"


@contextmanager
def trace_action(mower, name):
    """Counters are local to this integration instance, not device identities."""
    mower._action_sequence_id += 1
    label = f"{mower._action_sequence_id}:{name}"
    token = _ACTION.set((mower, label, asyncio.current_task()))
    outcome = "completed"
    _LOGGER.debug("Mower action begin action=%s session=%s", label, mower.session_id)
    try:
        yield
    except BaseException as err:
        outcome = type(err).__name__
        raise
    finally:
        _LOGGER.debug(
            "Mower action end action=%s session=%s outcome=%s",
            label, mower.session_id, outcome,
        )
        _ACTION.reset(token)
