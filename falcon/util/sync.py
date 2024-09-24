from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from functools import wraps
import inspect
import os
from typing import Any, Awaitable, Callable, Optional, TypeVar, Union

from falcon.util import deprecation

__all__ = (
    'async_to_sync',
    'create_task',
    'get_running_loop',
    'runs_sync',
    'sync_to_async',
    'wrap_sync_to_async',
    'wrap_sync_to_async_unsafe',
)

Result = TypeVar('Result')


class _DummyRunner:
    def run(self, coro: Awaitable[Result]) -> Result:  # pragma: nocover
        # NOTE(vytas): Work around get_event_loop deprecation in 3.10 by going
        #   via get_event_loop_policy(). This should be equivalent for
        #   async_to_sync's use case as it is currently impossible to invoke
        #   run_until_complete() from a running loop anyway.
        return self.get_loop().run_until_complete(coro)

    def get_loop(self) -> asyncio.AbstractEventLoop:  # pragma: nocover
        return asyncio.get_event_loop_policy().get_event_loop()

    def close(self) -> None:  # pragma: nocover
        pass


class _ActiveRunner:
    def __init__(self, runner_cls: type):
        self._runner_cls = runner_cls
        self._runner = runner_cls()

    # TODO(vytas): This typing is wrong on py311+, but mypy accepts it.
    #   It doesn't, OTOH, accept any of my ostensibly valid attempts to
    #   describe it.
    def __call__(self) -> _DummyRunner:
        # NOTE(vytas): Sometimes our runner's loop can get picked and consumed
        #   by other utilities and test methods. If that happens, recreate the runner.
        if self._runner.get_loop().is_closed():
            # NOTE(vytas): This condition is never hit on _DummyRunner.
            self._runner = self._runner_cls()  # pragma: nocover
        return self._runner


_active_runner = _ActiveRunner(getattr(asyncio, 'Runner', _DummyRunner))
_one_thread_to_rule_them_all = ThreadPoolExecutor(max_workers=1)

create_task = deprecation.deprecated(
    'This alias is deprecated; it will be removed in Falcon 5.0. '
    'Please use asyncio.create_task() directly.'
)(asyncio.create_task)
get_running_loop = deprecation.deprecated(
    'This alias is deprecated; it will be removed in Falcon 5.0. '
    'Please use asyncio.get_running_loop() directly.'
)(asyncio.get_running_loop)


def wrap_sync_to_async_unsafe(func: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a callable in a coroutine that executes the callable directly.

    This helper makes it easier to use synchronous callables with ASGI
    apps. However, it is considered "unsafe" because it calls the wrapped
    function directly in the same thread as the asyncio loop. Generally, you
    should use :func:`~.wrap_sync_to_async` instead.

    Warning:
        This helper is only to be used for functions that do not perform any
        blocking I/O or lengthy CPU-bound operations, since the entire async
        loop will be blocked while the wrapped function is executed.
        For a safer, non-blocking alternative that runs the function in a
        thread pool executor, use :func:`~.sync_to_async` instead.

    Arguments:
        func (callable): Function, method, or other callable to wrap

    Returns:
        function: An awaitable coroutine function that wraps the
        synchronous callable.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Callable[..., Any]:
        return func(*args, **kwargs)

    return wrapper


def wrap_sync_to_async(
    func: Callable[..., Any], threadsafe: Optional[bool] = None
) -> Callable[..., Any]:
    """Wrap a callable in a coroutine that executes the callable in the background.

    This helper makes it easier to call functions that can not be
    ported to use async natively (e.g., functions exported by a database
    library that does not yet support asyncio).

    To execute blocking operations safely, without stalling the async
    loop, the wrapped callable is scheduled to run in the background, on a
    separate thread, when the wrapper is called.

    Normally, the default executor for the running loop is used to schedule the
    synchronous callable. If the callable is not thread-safe, it can be
    scheduled serially in a global single-threaded executor.

    Warning:
        Wrapping a synchronous function safely adds a fair amount of overhead
        to the function call, and should only be used when a native async
        library is not available for the operation you wish to perform.

    Arguments:
        func (callable): Function, method, or other callable to wrap

    Keyword Arguments:
        threadsafe (bool): Set to ``False`` when the callable is not
            thread-safe (default ``True``). When this argument is ``False``,
            the wrapped callable will be scheduled to run serially in a
            global single-threaded executor.

    Returns:
        function: An awaitable coroutine function that wraps the
        synchronous callable.
    """

    if threadsafe is None or threadsafe:
        executor = None  # Use default
    else:
        executor = _one_thread_to_rule_them_all

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return await asyncio.get_running_loop().run_in_executor(
            executor, partial(func, *args, **kwargs)
        )

    return wrapper


async def sync_to_async(
    func: Callable[..., Any], *args: Any, **kwargs: Any
) -> Callable[..., Awaitable[Any]]:
    """Schedule a synchronous callable on the default executor and await the result.

    This helper makes it easier to call functions that can not be
    ported to use async natively (e.g., functions exported by a database
    library that does not yet support asyncio).

    To execute blocking operations safely, without stalling the async
    loop, the wrapped callable is scheduled to run in the background, on a
    separate thread, when the wrapper is called.

    The default executor for the running loop is used to schedule the
    synchronous callable.

    Warning:
        This helper can only be used to execute thread-safe callables. If
        the callable is not thread-safe, it can be executed serially
        by first wrapping it with :func:`~.wrap_sync_to_async`, and then
        executing the wrapper directly.

    Warning:
        Calling a synchronous function safely from an asyncio event loop
        adds a fair amount of overhead to the function call, and should
        only be used when a native async library is not available for the
        operation you wish to perform.

    Arguments:
        func (callable): Function, method, or other callable to wrap
        *args: All additional arguments are passed through to the callable.

    Keyword Arguments:
        **kwargs: All keyword arguments are passed through to the callable.

    Returns:
        function: An awaitable coroutine function that wraps the
        synchronous callable.
    """

    return await asyncio.get_running_loop().run_in_executor(
        None, partial(func, *args, **kwargs)
    )


def _should_wrap_non_coroutines() -> bool:
    """Return ``True`` IFF ``FALCON_ASGI_WRAP_NON_COROUTINES`` is set in the environ.

    This should only be used for Falcon's own test suite.
    """
    return 'FALCON_ASGI_WRAP_NON_COROUTINES' in os.environ


def _wrap_non_coroutine_unsafe(
    func: Optional[Callable[..., Any]],
) -> Union[Callable[..., Awaitable[Any]], Callable[..., Any], None]:
    """Wrap a coroutine using ``wrap_sync_to_async_unsafe()`` for internal test cases.

    This method is intended for Falcon's own test suite and should not be
    used by apps themselves. It provides a convenient way to reuse sync
    methods for ASGI test cases when it is safe to do so.

    Arguments:
        func (callable): Function, method, or other callable to wrap
    Returns:
        When not in test mode, this function simply returns the callable
        unchanged. Otherwise, if the callable is not a coroutine function,
        it will be wrapped using ``wrap_sync_to_async_unsafe()``.
    """

    if func is None:
        return func

    if not _should_wrap_non_coroutines():
        return func

    if inspect.iscoroutinefunction(func):
        return func

    return wrap_sync_to_async_unsafe(func)


def async_to_sync(
    coroutine: Callable[..., Awaitable[Result]], *args: Any, **kwargs: Any
) -> Result:
    """Invoke a coroutine function from a synchronous caller.

    This method can be used to invoke an asynchronous task from a synchronous
    context. The coroutine will be scheduled to run on the current event
    loop for the current OS thread. If an event loop is not already running,
    one will be created.

    Warning:
        Executing async code in this manner is inefficient since it involves
        synchronization via threading primitives, and is intended primarily for
        testing, prototyping or compatibility purposes.

    Note:
        On Python 3.11+, this function leverages a module-wide
        ``asyncio.Runner``.

    Args:
        coroutine: A coroutine function to invoke.
        *args: Additional args are passed through to the coroutine function.

    Keyword Args:
        **kwargs: Additional args are passed through to the coroutine function.
    """
    return _active_runner().run(coroutine(*args, **kwargs))


def runs_sync(coroutine: Callable[..., Awaitable[Result]]) -> Callable[..., Result]:
    """Transform a coroutine function into a synchronous method.

    This is achieved by always invoking the decorated coroutine function via
    :meth:`async_to_sync`.

    Warning:
        This decorator is very inefficient and should only be used for adapting
        asynchronous test functions for use with synchronous test runners such
        as ``pytest`` or the ``unittest`` module.

        It will create an event loop for the current thread if one is not
        already running.

    Args:
        coroutine: A coroutine function to masquerade as a synchronous one.

    Returns:
        callable: A synchronous function.
    """

    @wraps(coroutine)
    def invoke(*args: Any, **kwargs: Any) -> Any:
        return async_to_sync(coroutine, *args, **kwargs)

    return invoke
