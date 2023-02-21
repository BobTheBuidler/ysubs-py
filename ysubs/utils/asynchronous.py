
import asyncio
import functools
from typing import Awaitable, Callable, TypeVar

from typing_extensions import ParamSpec

T = TypeVar("T")
P = ParamSpec("P")

def await_if_sync(coro_fn: Callable[P, T]) -> Callable[P, T]:
    @functools.wraps(coro_fn)
    def await_wrapper(self, *args: P.args, **kwargs: P.kwargs) -> T:
        coro = coro_fn(self, *args, **kwargs)
        if self.asynchronous == True:
            return coro
        elif self.asynchronous == False:
            return asyncio.get_event_loop().run_until_complete(coro)
        raise ValueError(f"'asynchronous' must be a boolean value. You passed {self.asynchronous}")
    return await_wrapper