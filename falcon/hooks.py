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

from functools import wraps
from inspect import getmembers
import re

from falcon import COMBINED_METHODS
from falcon.util import compat
from falcon.util.misc import get_argnames


_DECORABLE_METHOD_NAME = re.compile(r'^on_({})(_\w+)?$'.format(
    '|'.join(method.lower() for method in COMBINED_METHODS)))


def before(action, *args, **kwargs):
    """Decorator to execute the given action function *before* the responder.

    Args:
        action (callable): A function of the form
            ``func(req, resp, resource, params)``, where `resource` is a
            reference to the resource class instance associated with the
            request, and `params` is a dict of URI Template field names,
            if any, that will be passed into the resource responder as
            kwargs.

            Note:
                Hooks may inject extra params as needed. For example::

                    def do_something(req, resp, resource, params):
                        try:
                            params['id'] = int(params['id'])
                        except ValueError:
                            raise falcon.HTTPBadRequest('Invalid ID',
                                                        'ID was not valid.')

                        params['answer'] = 42

        *args: Any additional arguments will be passed to *action* in the
            order given, immediately following the *req*, *resp*, *resource*,
            and *params* arguments.

        **kwargs: Any additional keyword arguments will be passed through to
            *action*.
    """

    def _before(responder_or_resource):
        if isinstance(responder_or_resource, compat.class_types):
            resource = responder_or_resource

            for responder_name, responder in getmembers(resource, callable):
                if _DECORABLE_METHOD_NAME.match(responder_name):
                    # This pattern is necessary to capture the current value of
                    # responder in the do_before_all closure; otherwise, they
                    # will capture the same responder variable that is shared
                    # between iterations of the for loop, above.
                    def let(responder=responder):
                        do_before_all = _wrap_with_before(responder, action, args, kwargs)

                        setattr(resource, responder_name, do_before_all)

                    let()

            return resource

        else:
            responder = responder_or_resource
            do_before_one = _wrap_with_before(responder, action, args, kwargs)

            return do_before_one

    return _before


def after(action, *args, **kwargs):
    """Decorator to execute the given action function *after* the responder.

    Args:
        action (callable): A function of the form
            ``func(req, resp, resource)``, where `resource` is a
            reference to the resource class instance associated with the
            request

        *args: Any additional arguments will be passed to *action* in the
            order given, immediately following the *req*, *resp*, *resource*,
            and *params* arguments.

        **kwargs: Any additional keyword arguments will be passed through to
            *action*.
    """

    def _after(responder_or_resource):
        if isinstance(responder_or_resource, compat.class_types):
            resource = responder_or_resource

            for responder_name, responder in getmembers(resource, callable):
                if _DECORABLE_METHOD_NAME.match(responder_name):
                    def let(responder=responder):
                        do_after_all = _wrap_with_after(responder, action, args, kwargs)

                        setattr(resource, responder_name, do_after_all)

                    let()

            return resource

        else:
            responder = responder_or_resource
            do_after_one = _wrap_with_after(responder, action, args, kwargs)

            return do_after_one

    return _after


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _wrap_with_after(responder, action, action_args, action_kwargs):
    """Execute the given action function after a responder method.

    Args:
        responder: The responder method to wrap.
        action: A function with a signature similar to a resource responder
            method, taking the form ``func(req, resp, resource)``.
        action_args: Additional positional agruments to pass to *action*.
        action_kwargs: Additional keyword arguments to pass to *action*.
    """

    responder_argnames = get_argnames(responder)
    extra_argnames = responder_argnames[2:]  # Skip req, resp

    @wraps(responder)
    def do_after(self, req, resp, *args, **kwargs):
        if args:
            _merge_responder_args(args, kwargs, extra_argnames)

        responder(self, req, resp, **kwargs)
        action(req, resp, self, *action_args, **action_kwargs)

    return do_after


def _wrap_with_before(responder, action, action_args, action_kwargs):
    """Execute the given action function before a responder method.

    Args:
        responder: The responder method to wrap.
        action: A function with a similar signature to a resource responder
            method, taking the form ``func(req, resp, resource, params)``.
        action_args: Additional positional agruments to pass to *action*.
        action_kwargs: Additional keyword arguments to pass to *action*.
    """

    responder_argnames = get_argnames(responder)
    extra_argnames = responder_argnames[2:]  # Skip req, resp

    @wraps(responder)
    def do_before(self, req, resp, *args, **kwargs):
        if args:
            _merge_responder_args(args, kwargs, extra_argnames)

        action(req, resp, self, kwargs, *action_args, **action_kwargs)
        responder(self, req, resp, **kwargs)

    return do_before


def _merge_responder_args(args, kwargs, argnames):
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
        # which wont be in the args list, and are already in the kwargs
        # dict anyway, so detect and skip them.
        if argname not in kwargs:
            kwargs[argname] = args[i]
