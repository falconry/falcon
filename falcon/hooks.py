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

from collections.abc import Awaitable
from functools import wraps
from inspect import getmembers
from inspect import iscoroutinefunction
import os
import re
from typing import (
    Any,
    Callable,
    cast,
    TYPE_CHECKING,
    TypeVar,
    Union,
)
import warnings

from falcon.constants import COMBINED_METHODS
from falcon.constants import TRUE_STRINGS
from falcon.util.misc import get_argnames
from falcon.util.sync import _wrap_non_coroutine_unsafe

if TYPE_CHECKING:
    from typing import Concatenate, ParamSpec

    import falcon as wsgi
    from falcon import asgi
    from falcon._typing import AsgiResponderMethod
    from falcon._typing import Resource
    from falcon._typing import Responder
    from falcon._typing import ResponderMethod

    _FN = ParamSpec('_FN')

_R = TypeVar('_R', bound=Union['Responder', 'Resource'])


_DECORABLE_METHOD_NAME = re.compile(
    r'^on_({})(_\w+)?$'.format('|'.join(method.lower() for method in COMBINED_METHODS))
)

_ON_REQUEST_SKIPPED_WARNING = (
    'Skipping decoration of default responder {responder_name!r} on resource '
    '{resource_name!r}. To enable decorating default responders with '
    'class-level hooks, set falcon.hooks.decorate_on_request to True '
    '(or set the environment variable FALCON_DECORATE_ON_REQUEST=1).'
)

decorate_on_request = os.environ.get('FALCON_DECORATE_ON_REQUEST', '0') in TRUE_STRINGS
"""Apply class-level hooks to ``on_request`` (and ``on_request_{suffix}``) methods.

This module-level attribute is disabled by default; wrapping default responders
with class-level hooks can be enabled by setting the value of
`decorate_on_request` to ``True``::

    import falcon.hooks
    falcon.hooks.decorate_on_request = True

The value of this attribute must be patched before importing a module where
resource classes are actually decorated. In the case setting this value
beforehand is not possible, wrapping default responders with class-level hooks
can also be enabled by setting the ``FALCON_DECORATE_ON_REQUEST`` environment
variable to a truthy value. For example:

.. code:: bash

    $ export FALCON_DECORATE_ON_REQUEST=1
"""


def before(
    action: Callable[
        Concatenate[wsgi.Request, wsgi.Response, Resource, dict[str, Any], _FN], None
    ]
    | Callable[
        Concatenate[asgi.Request, asgi.Response, Resource, dict[str, Any], _FN],
        Awaitable[None],
    ],
    *args: _FN.args,
    **kwargs: _FN.kwargs,
) -> Callable[[_R], _R]:
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

                if re.compile(r'^on_request(_\w+)?$').match(responder_name):
                    # Only wrap default responders if decorate_on_request is set to True
                    if decorate_on_request:
                        responder = cast('Responder', responder)
                        do_before_all = _wrap_with_before(
                            responder, action, args, kwargs
                        )

                        setattr(responder_or_resource, responder_name, do_before_all)
                    else:
                        warnings.warn(
                            _ON_REQUEST_SKIPPED_WARNING.format(
                                responder_name=responder_name,
                                resource_name=responder_or_resource.__name__,
                            ),
                            UserWarning,
                        )

            return cast(_R, responder_or_resource)

        else:
            responder = cast('Responder', responder_or_resource)
            do_before_one = _wrap_with_before(responder, action, args, kwargs)

            return cast(_R, do_before_one)

    return _before


def after(
    action: Callable[Concatenate[wsgi.Request, wsgi.Response, Resource, _FN], None]
    | Callable[
        Concatenate[asgi.Request, asgi.Response, Resource, _FN], Awaitable[None]
    ],
    *args: _FN.args,
    **kwargs: _FN.kwargs,
) -> Callable[[_R], _R]:
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

                if re.compile(r'^on_request(_\w+)?$').match(responder_name):
                    # Only wrap default responders if decorate_on_request is set to True
                    if decorate_on_request:
                        responder = cast('Responder', responder)
                        do_after_all = _wrap_with_after(responder, action, args, kwargs)

                        setattr(responder_or_resource, responder_name, do_after_all)
                    else:
                        warnings.warn(
                            _ON_REQUEST_SKIPPED_WARNING.format(
                                responder_name=responder_name,
                                resource_name=responder_or_resource.__name__,
                            ),
                            UserWarning,
                        )

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
    responder: Responder,
    action: Callable[..., None | Awaitable[None]],
    action_args: Any,
    action_kwargs: Any,
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
        async_action = cast(
            Callable[..., Awaitable[None]], _wrap_non_coroutine_unsafe(action)
        )
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
        sync_action = cast(Callable[..., None], action)
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
    action: Callable[..., None | Awaitable[None]],
    action_args: tuple[Any, ...],
    action_kwargs: dict[str, Any],
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
        async_action = cast(
            Callable[..., Awaitable[None]], _wrap_non_coroutine_unsafe(action)
        )
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
        sync_action = cast(Callable[..., None], action)
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
    args: tuple[Any, ...], kwargs: dict[str, Any], argnames: list[str]
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
