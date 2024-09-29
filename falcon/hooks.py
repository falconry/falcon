# Copyright 2013 by Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Hook decorators."""

from __future__ import annotations

from functools import wraps
from inspect import getmembers
from inspect import iscoroutinefunction
import re
from typing import (
    Any,
    Awaitable,
    Callable,
    cast,
    Dict,
    List,
    Protocol,
    Tuple,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

from falcon.constants import COMBINED_METHODS
from falcon.util.misc import get_argnames
from falcon.util.sync import _wrap_non_coroutine_unsafe

if TYPE_CHECKING:
    import falcon as wsgi
    from falcon import asgi
    from falcon._typing import AsgiResponderMethod
    from falcon._typing import Resource
    from falcon._typing import Responder
    from falcon._typing import ResponderMethod


# TODO: when targeting only 3.10+ these protocol would no longer be needed, since
# ParamSpec could be used together with Concatenate to use a simple Callable
# to type the before and after functions. This approach was prototyped in
# https://github.com/falconry/falcon/pull/2234
class SyncBeforeFn(Protocol):
    def __call__(
        self,
        req: wsgi.Request,
        resp: wsgi.Response,
        resource: Resource,
        params: Dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> None: ...


class AsyncBeforeFn(Protocol):
    def __call__(
        self,
        req: asgi.Request,
        resp: asgi.Response,
        resource: Resource,
        params: Dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> Awaitable[None]: ...


BeforeFn = Union[SyncBeforeFn, AsyncBeforeFn]


class SyncAfterFn(Protocol):
    def __call__(
        self,
        req: wsgi.Request,
        resp: wsgi.Response,
        resource: Resource,
        *args: Any,
        **kwargs: Any,
    ) -> None: ...


class AsyncAfterFn(Protocol):
    def __call__(
        self,
        req: asgi.Request,
        resp: asgi.Response,
        resource: Resource,
        *args: Any,
        **kwargs: Any,
    ) -> Awaitable[None]: ...


AfterFn = Union[SyncAfterFn, AsyncAfterFn]
_R = TypeVar('_R', bound=Union['Responder', 'Resource'])


_DECORABLE_METHOD_NAME = re.compile(
    r'^on_({})(_\w+)?$'.format('|'.join(method.lower() for method in COMBINED_METHODS))
)


def before(action: BeforeFn, *args: Any, **kwargs: Any) -> Callable[[_R], _R]:
    """Execute the given action function *before* the responder.

    The `params` argument that is passed to the hook
    contains only the fields from the URI template path; it does not
    include query string values.

    Hooks may inject extra params as needed. For example::

        def do_something(req, resp, resource, params):
            try:
                params['id'] = int(params['id'])
            except ValueError:
                raise falcon.HTTPBadRequest(title='Invalid ID',
                                            description='ID was not valid.')

            params['answer'] = 42

    Args:
        action (callable): A function of the form
            ``func(req, resp, resource, params)``, where `resource` is a
            reference to the resource class instance associated with the
            request and `params` is a dict of URI template field names,
            if any, that will be passed into the resource responder as
            kwargs.

        *args: Any additional arguments will be passed to *action* in the
            order given, immediately following the *req*, *resp*, *resource*,
            and *params* arguments.

    Keyword Args:
        **kwargs: Any additional keyword arguments will be passed through to
            *action*.
    """

    def _before(responder_or_resource: _R) -> _R:
        if isinstance(responder_or_resource, type):
            for responder_name, responder in getmembers(
                responder_or_resource, callable
            ):
                if _DECORABLE_METHOD_NAME.match(responder_name):
                    responder = cast('Responder', responder)
                    do_before_all = _wrap_with_before(responder, action, args, kwargs)

                    setattr(responder_or_resource, responder_name, do_before_all)

            return cast(_R, responder_or_resource)

        else:
            responder = cast('Responder', responder_or_resource)
            do_before_one = _wrap_with_before(responder, action, args, kwargs)

            return cast(_R, do_before_one)

    return _before


def after(action: AfterFn, *args: Any, **kwargs: Any) -> Callable[[_R], _R]:
    """Execute the given action function *after* the responder.

    Args:
        action (callable): A function of the form
            ``func(req, resp, resource)``, where `resource` is a
            reference to the resource class instance associated with the
            request

        *args: Any additional arguments will be passed to *action* in the
            order given, immediately following the *req*, *resp* and *resource*
            arguments.

    Keyword Args:
        **kwargs: Any additional keyword arguments will be passed through to
            *action*.
    """

    def _after(responder_or_resource: _R) -> _R:
        if isinstance(responder_or_resource, type):
            for responder_name, responder in getmembers(
                responder_or_resource, callable
            ):
                if _DECORABLE_METHOD_NAME.match(responder_name):
                    responder = cast('Responder', responder)
                    do_after_all = _wrap_with_after(responder, action, args, kwargs)

                    setattr(responder_or_resource, responder_name, do_after_all)

            return cast(_R, responder_or_resource)

        else:
            responder = cast('Responder', responder_or_resource)
            do_after_one = _wrap_with_after(responder, action, args, kwargs)

            return cast(_R, do_after_one)

    return _after


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _wrap_with_after(
    responder: Responder, action: AfterFn, action_args: Any, action_kwargs: Any
) -> Responder:
    """Execute the given action function after a responder method.

    Args:
        responder: The responder method to wrap.
        action: A function with a signature similar to a resource responder
            method, taking the form ``func(req, resp, resource)``.
        action_args: Additional positional arguments to pass to *action*.
        action_kwargs: Additional keyword arguments to pass to *action*.
    """

    responder_argnames = get_argnames(responder)
    extra_argnames = responder_argnames[2:]  # Skip req, resp
    do_after_responder: Responder

    if iscoroutinefunction(responder):
        async_action = cast('AsyncAfterFn', _wrap_non_coroutine_unsafe(action))
        async_responder = cast('AsgiResponderMethod', responder)

        @wraps(async_responder)
        async def do_after(
            self: Resource,
            req: asgi.Request,
            resp: asgi.Response,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            if args:
                _merge_responder_args(args, kwargs, extra_argnames)

            await async_responder(self, req, resp, **kwargs)
            await async_action(req, resp, self, *action_args, **action_kwargs)

        do_after_responder = cast('AsgiResponderMethod', do_after)
    else:
        sync_action = cast('SyncAfterFn', action)
        sync_responder = cast('ResponderMethod', responder)

        @wraps(sync_responder)
        def do_after(
            self: Resource,
            req: wsgi.Request,
            resp: wsgi.Response,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            if args:
                _merge_responder_args(args, kwargs, extra_argnames)

            sync_responder(self, req, resp, **kwargs)
            sync_action(req, resp, self, *action_args, **action_kwargs)

        do_after_responder = cast('ResponderMethod', do_after)
    return do_after_responder


def _wrap_with_before(
    responder: Responder,
    action: BeforeFn,
    action_args: Tuple[Any, ...],
    action_kwargs: Dict[str, Any],
) -> Responder:
    """Execute the given action function before a responder method.

    Args:
        responder: The responder method to wrap.
        action: A function with a similar signature to a resource responder
            method, taking the form ``func(req, resp, resource, params)``.
        action_args: Additional positional arguments to pass to *action*.
        action_kwargs: Additional keyword arguments to pass to *action*.
    """

    responder_argnames = get_argnames(responder)
    extra_argnames = responder_argnames[2:]  # Skip req, resp
    do_before_responder: Responder

    if iscoroutinefunction(responder):
        async_action = cast('AsyncBeforeFn', _wrap_non_coroutine_unsafe(action))
        async_responder = cast('AsgiResponderMethod', responder)

        @wraps(async_responder)
        async def do_before(
            self: Resource,
            req: asgi.Request,
            resp: asgi.Response,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            if args:
                _merge_responder_args(args, kwargs, extra_argnames)

            await async_action(req, resp, self, kwargs, *action_args, **action_kwargs)
            await async_responder(self, req, resp, **kwargs)

        do_before_responder = cast('AsgiResponderMethod', do_before)
    else:
        sync_action = cast('SyncBeforeFn', action)
        sync_responder = cast('ResponderMethod', responder)

        @wraps(sync_responder)
        def do_before(
            self: Resource,
            req: wsgi.Request,
            resp: wsgi.Response,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            if args:
                _merge_responder_args(args, kwargs, extra_argnames)

            sync_action(req, resp, self, kwargs, *action_args, **action_kwargs)
            sync_responder(self, req, resp, **kwargs)

        do_before_responder = cast('ResponderMethod', do_before)
    return do_before_responder


def _merge_responder_args(
    args: Tuple[Any, ...], kwargs: Dict[str, Any], argnames: List[str]
) -> None:
    """Merge responder args into kwargs.

    The framework always passes extra args as keyword arguments.
    However, when the app calls the responder directly, it might use
    positional arguments instead, so we need to handle that case. This
    might happen, for example, when overriding a resource and calling
    a responder via super().

    Args:
        args (tuple): Extra args passed into the responder
        kwargs (dict): Keyword args passed into the responder
        argnames (list): Extra argnames from the responder's
            signature, ordered as defined
    """

    # NOTE(kgriffs): Merge positional args into kwargs by matching
    # them up to the responder's signature. To do that, we must
    # find out the names of the positional arguments by matching
    # them in the order of the arguments named in the responder's
    # signature.
    for i, argname in enumerate(argnames):
        # NOTE(kgriffs): extra_argnames may contain keyword arguments,
        # which won't be in the args list, and are already in the kwargs
        # dict anyway, so detect and skip them.
        if argname not in kwargs:
            kwargs[argname] = args[i]
