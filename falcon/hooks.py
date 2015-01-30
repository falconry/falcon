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
        action (callable): A function of the form
            ``func(req, resp, resource)``, where `resource` is a
            reference to the resource class instance associated with the
            request

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


# NOTE(kgriffs): Coverage disabled because under Python 3.4, the exception
# is never raised. Coverage has been verified when running under other
# versions of Python.
def _get_argspec(func):  # pragma: no cover
    """Wrapper around inspect.getargspec to handle Py2/Py3 differences."""

    try:
        # NOTE(kgriffs): This will fail for callable classes, which
        # explicitly define __call__, except under Python 3.4.
        spec = inspect.getargspec(func)

    except TypeError:
        # NOTE(kgriffs): If this is a class that defines __call__ as a
        # method, we need to get the argspec of __call__ directly. This
        # does not work for regular functions and methods, because in
        # that case, __call__ isn't actually a Python function under
        # Python 2.6-3.3 (fixed in 3.4).
        spec = inspect.getargspec(func.__call__)

    return spec


def _has_self(spec):
    """Checks whether the given argspec includes a self param.

    Warning:
        If a method's spec lists "self", that doesn't necessarily mean
        that it should be called with a `self` param; if the method
        instance is bound, the caller must omit `self` on invocation.

    """

    return len(spec.args) > 0 and spec.args[0] == 'self'


def _wrap_with_after(action, responder, resource=None, is_method=False):
    """Execute the given action function after a responder method.

    Args:
        action: A function with a signature similar to a resource responder
            method, taking the form ``func(req, resp, resource)``.
        responder: The responder method to wrap.
        resource: The resource affected by `action` (default ``None``). If
            ``None``, `is_method` MUST BE True, so that the resource can be
            derived from the `self` param that is passed into the wrapper.
        is_method: Whether or not `responder` is an unbound method
            (default ``False``).

    """

    # NOTE(swistakm): introspect action function to guess if it can handle
    # additional resource argument without breaking backwards compatibility
    spec = _get_argspec(action)

    # NOTE(swistakm): create shim before checking what will be actually
    # decorated. This helps to avoid excessive nesting
    if len(spec.args) == (4 if _has_self(spec) else 3):
        shim = action
    else:
        # TODO(kgriffs): This decorator does not work on callable
        # classes in Python vesions prior to 3.4.
        #
        # @wraps(action)
        def shim(req, resp, resource):
            action(req, resp)

    # NOTE(swistakm): method must be decorated differently than
    # normal function
    if is_method:
        @wraps(responder)
        def do_after(self, req, resp, **kwargs):
            responder(self, req, resp, **kwargs)
            shim(req, resp, self)
    else:
        assert resource is not None

        @wraps(responder)
        def do_after(req, resp, **kwargs):
            responder(req, resp, **kwargs)
            shim(req, resp, resource)

    return do_after


def _wrap_with_before(action, responder, resource=None, is_method=False):
    """Execute the given action function before a responder method.

    Args:
        action: A function with a similar signature to a resource responder
            method, taking the form ``func(req, resp, resource, params)``.
        responder: The responder method to wrap
        resource: The resource affected by `action` (default ``None``). If
            ``None``, `is_method` MUST BE True, so that the resource can be
            derived from the `self` param that is passed into the wrapper
        is_method: Whether or not `responder` is an unbound method
            (default ``False``)

    """

    # NOTE(swistakm): introspect action function to guess if it can handle
    # additional resource argument without breaking backwards compatibility
    action_spec = _get_argspec(action)

    # NOTE(swistakm): create shim before checking what will be actually
    # decorated. This allows to avoid excessive nesting
    if len(action_spec.args) == (5 if _has_self(action_spec) else 4):
        shim = action
    else:
        # TODO(kgriffs): This decorator does not work on callable
        # classes in Python vesions prior to 3.4.
        #
        # @wraps(action)
        def shim(req, resp, resource, kwargs):
            # NOTE(kgriffs): Don't have to pass "self" even if has_self,
            # since method is assumed to be bound.
            action(req, resp, kwargs)

    # NOTE(swistakm): method must be decorated differently than
    # normal function
    if is_method:
        @wraps(responder)
        def do_before(self, req, resp, **kwargs):
            shim(req, resp, self, kwargs)
            responder(self, req, resp, **kwargs)
    else:
        assert resource is not None

        @wraps(responder)
        def do_before(req, resp, **kwargs):
            shim(req, resp, resource, kwargs)
            responder(req, resp, **kwargs)

    return do_before


def _wrap_with_hooks(before, after, responder, resource):
    """Wrap responder on the given resource with "before" and "after" hooks.

    Args:
        before: An iterable of one or more "before" hooks
        after: An iterable of one or more "after" hooks
        responder: A method of a resource to wrap
        resource: A reference to the resource instance providing the responder

    """

    if after is not None:
        for action in after:
            responder = _wrap_with_after(action, responder, resource)

    if before is not None:
        # Wrap in reversed order to achieve natural (first...last)
        # execution order.
        for action in reversed(before):
            responder = _wrap_with_before(action, responder, resource)

    return responder
