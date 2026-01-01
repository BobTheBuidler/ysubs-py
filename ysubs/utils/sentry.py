from typing import TypeVar, Callable
from typing_extensions import ParamSpec

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None

P = ParamSpec("P")
T = TypeVar("T")


def trace(fn: Callable[P, T]) -> Callable[P, T]:
    return sentry_sdk.trace(fn) if sentry_sdk is not None else fn


def set_user(headers: dict) -> None:
    if sentry_sdk and "X-Signer" in headers:
        sentry_sdk.set_user({"id": headers["X-Signer"]})
