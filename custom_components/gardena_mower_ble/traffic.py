"""Defer background BLE reads during user action confirmation."""

from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

from .tracing import trace_action

BACKGROUND_READ = ContextVar("gardena_background_read", default=False)


@contextmanager
def foreground_read():
    """Keep heartbeat requests eligible even when their task inherited polling."""
    token = BACKGROUND_READ.set(False)
    try:
        yield
    finally:
        BACKGROUND_READ.reset(token)


def background_poll(method):
    @wraps(method)
    async def wrapped(*args, **kwargs):
        token = BACKGROUND_READ.set(True)
        try:
            return await method(*args, **kwargs)
        finally:
            BACKGROUND_READ.reset(token)
    return wrapped


def foreground_action(method):
    @wraps(method)
    async def wrapped(self, *args, **kwargs):
        with foreground_read(), trace_action(self.coordinator.mower, method.__name__):
            async with self.coordinator.mower.lock.action_window():
                return await method(self, *args, **kwargs)
    return wrapped
