import asyncio
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from functools import partial, wraps
import inspect
import os


__all__ = [
    'get_loop',
    'sync_to_async',
    'wrap_sync_to_async',
    'wrap_sync_to_async_unsafe',
]


_one_thread_to_rule_them_all = ThreadPoolExecutor(max_workers=1)


try:
    get_loop = asyncio.get_running_loop
    """Gets the running asyncio event loop."""
except AttributeError:  # pragma: nocover
    # NOTE(kgriffs): This branch is definitely covered under py35 and py36
    #   but for some reason the codecov gate doesn't pick this up, hence
    #   the pragma above.

    get_loop = asyncio.get_event_loop
    """Gets the running asyncio event loop."""


def wrap_sync_to_async_unsafe(func) -> Coroutine:
    """Wrap a callable in a coroutine that executes the callable directly.

    This helper makes it easier to use synchronous callables with ASGI
    apps. However, it is considered "unsafe" because it calls the wrapped
    function directly in the same thread as the asyncio loop. Generally, you
    should use :meth:`~.wrap_sync_to_async` instead.

    Warning:
        This helper is only to be used for functions that do not perform any
        blocking I/O or lengthy CPU-bound operations, since the entire async
        loop will be blocked while the wrapped function is executed.
        For a safer, non-blocking alternative that runs the function in a
        thread pool executor, use :func:~.sync_to_async instead.

    Arguments:
        func (callable): Function, method, or other callable to wrap

    Returns:
        function: An awaitable coroutine function that wraps the
        synchronous callable.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def wrap_sync_to_async(func, threadsafe=None) -> Coroutine:
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
    async def wrapper(*args, **kwargs):
        return await get_loop().run_in_executor(executor, partial(func, *args, **kwargs))

    return wrapper


async def sync_to_async(func, *args, **kwargs):
    """Schedules a synchronous callable on the loop's default executor and awaits the result.

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
        by first wrapping it with :meth:`~.wrap_sync_to_async`, and then
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

    return await get_loop().run_in_executor(None, partial(func, *args, **kwargs))


def _should_wrap_non_coroutines() -> bool:
    """Returns True IFF FALCON_ASGI_WRAP_NON_COROUTINES is set in the environ.

    This should only be used for Falcon's own test suite.
    """

    return 'FALCON_ASGI_WRAP_NON_COROUTINES' in os.environ


def _wrap_non_coroutine_unsafe(func):
    """Wraps a coroutine using ``wrap_sync_to_async_unsafe()`` for internal test cases.

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
