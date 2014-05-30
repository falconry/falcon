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

from functools import wraps
import inspect

import six

from falcon import HTTP_METHODS


def before(action):
    """Decorator to execute the given action function *before* the responder.

    Args:
        action (callable): A function of the form ``func(req, resp, params)``,
            where params is a dict of URI Template field names, if any,
            that will be passed into the resource responder as *kwargs*.

            Hooks may inject extra params as needed. For example::

                def do_something(req, resp, params):
                    try:
                        params['id'] = int(params['id'])
                    except ValueError:
                        raise falcon.HTTPBadRequest('Invalid ID',
                                                    'ID was not valid.')

                    params['answer'] = 42

    """

    def _before(responder_or_resource):
        if isinstance(responder_or_resource, six.class_types):
            resource = responder_or_resource

            for method in HTTP_METHODS:
                responder_name = 'on_' + method.lower()

                try:
                    responder = getattr(resource, responder_name)
                except AttributeError:
                    # resource does not implement this method
                    pass
                else:
                    # Usually expect a method, but any callable will do
                    if callable(responder):
                        # This pattern is necessary to capture the current
                        # value of responder in the do_before_all closure;
                        # otherwise, they will capture the same responder
                        # variable that is shared between iterations of the
                        # for loop, above.
                        def let(responder=responder):
                            do_before_all = _wrap_with_before(
                                action, responder, resource, True)

                            setattr(resource, responder_name, do_before_all)

                        let()

            return resource

        else:
            responder = responder_or_resource
            do_before_one = _wrap_with_before(action, responder, None, True)

            return do_before_one

    return _before


def after(action):
    """Decorator to execute the given action function *after* the responder.

    Args:
        action (callable): A function of the form ``func(req, resp)``

    """

    def _after(responder_or_resource):
        if isinstance(responder_or_resource, six.class_types):
            resource = responder_or_resource

            for method in HTTP_METHODS:
                responder_name = 'on_' + method.lower()

                try:
                    responder = getattr(resource, responder_name)
                except AttributeError:
                    # resource does not implement this method
                    pass
                else:
                    # Usually expect a method, but any callable will do
                    if callable(responder):

                        def let(responder=responder):
                            do_after_all = _wrap_with_after(
                                action, responder, resource, True)

                            setattr(resource, responder_name, do_after_all)

                        let()

            return resource

        else:
            responder = responder_or_resource
            do_after_one = _wrap_with_after(action, responder, None, True)

            return do_after_one

    return _after

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _wrap_with_after(action, responder, resource, is_method=False):
    """Execute the given action function after a bound responder.

    Args:
        action: A function with a signature similar to a resource responder
            method, taking (req, resp).
        responder: The bound responder to wrap.
        resource: The resource affected by action.
        is_method: Is wrapped responder a class method?

    """
    # NOTE(swistakm): introspect action function do guess if it can handle
    # additionalresource argument without breaking backwards compatibility
    spec = inspect.getargspec(action)

    # NOTE(swistakm): create hook before checking what will be actually
    # decorated. This helps to avoid excessive nesting
    if len(spec.args) > 2:
        @wraps(action)
        def hook(req, resp, resource):
            action(req, resp, resource)
    else:
        @wraps(action)
        def hook(req, resp, resource):
            action(req, resp)

    # NOTE(swistakm): method must be decorated differently than normal function
    if is_method:
        @wraps(responder)
        def do_after(self, req, resp, **kwargs):
            responder(self, req, resp, **kwargs)
            hook(req, resp, self)
    else:
        @wraps(responder)
        def do_after(req, resp, **kwargs):
            responder(req, resp, **kwargs)
            hook(req, resp, resource)

    return do_after


def _wrap_with_before(action, responder, resource, is_method=False):
    """Execute the given action function before a bound responder.

    Args:
        action: A function with a similar signature to a resource responder
            method, taking (req, resp, params).
        responder: The bound responder to wrap.
        resource: The resource affected by action.
        is_method: Is wrapped responder a class method?

    """
    # NOTE(swistakm): introspect action function do guess if it can handle
    # additional resource argument without breaking backwards compatibility
    spec = inspect.getargspec(action)

    # NOTE(swistakm): create hook before checking what will be actually
    # decorated. This allows to avoid excessive nesting
    if len(spec.args) > 3:
        @wraps(action)
        def hook(req, resp, resource, kwargs):
            action(req, resp, resource, kwargs)
    else:
        @wraps(action)
        def hook(req, resp, resource, kwargs):
            action(req, resp, kwargs)

    # NOTE(swistakm): method must be decorated differently than normal function
    if is_method:
        @wraps(responder)
        def do_before(self, req, resp, **kwargs):
            hook(req, resp, self, kwargs)
            responder(self, req, resp, **kwargs)
    else:
        @wraps(responder)
        def do_before(req, resp, **kwargs):
            hook(req, resp, resource, kwargs)
            responder(req, resp, **kwargs)

    return do_before


def _wrap_with_hooks(before, after, responder, resource):
    if after is not None:
        for action in after:
            responder = _wrap_with_after(action, responder, resource)

    if before is not None:
        # Wrap in reversed order to achieve natural (first...last)
        # execution order.
        for action in reversed(before):
            responder = _wrap_with_before(action, responder, resource)

    return responder
