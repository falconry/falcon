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

import six

from falcon import HTTP_METHODS
from falcon.util.misc import get_argnames


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
                            do_before_all = _wrap_with_before(action, responder)

                            setattr(resource, responder_name, do_before_all)

                        let()

            return resource

        else:
            responder = responder_or_resource
            do_before_one = _wrap_with_before(action, responder)

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
                            do_after_all = _wrap_with_after(action, responder)

                            setattr(resource, responder_name, do_after_all)

                        let()

            return resource

        else:
            responder = responder_or_resource
            do_after_one = _wrap_with_after(action, responder)

            return do_after_one

    return _after


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _wrap_with_after(action, responder):
    """Execute the given action function after a responder method.

    Args:
        action: A function with a signature similar to a resource responder
            method, taking the form ``func(req, resp, resource)``.
        responder: The responder method to wrap.
    """

    # NOTE(swistakm): create shim before checking what will be actually
    # decorated. This helps to avoid excessive nesting
    if 'resource' in get_argnames(action):
        shim = action
    else:
        # TODO(kgriffs): This decorator does not work on callable
        # classes in Python vesions prior to 3.4.
        #
        # @wraps(action)
        def shim(req, resp, resource):
            action(req, resp)

    @wraps(responder)
    def do_after(self, req, resp, **kwargs):
        responder(self, req, resp, **kwargs)
        shim(req, resp, self)

    return do_after


def _wrap_with_before(action, responder):
    """Execute the given action function before a responder method.

    Args:
        action: A function with a similar signature to a resource responder
            method, taking the form ``func(req, resp, resource, params)``.
        responder: The responder method to wrap
    """

    # NOTE(swistakm): create shim before checking what will be actually
    # decorated. This allows to avoid excessive nesting
    if 'resource' in get_argnames(action):
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

    @wraps(responder)
    def do_before(self, req, resp, **kwargs):
        shim(req, resp, self, kwargs)
        responder(self, req, resp, **kwargs)

    return do_before
