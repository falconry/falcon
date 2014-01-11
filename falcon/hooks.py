"""Defines Falcon hooks

Copyright 2013 by Rackspace Hosting, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

from functools import wraps
import six

from falcon import HTTP_METHODS
from falcon import api_helpers


def before(action):
    """Decorator to execute the given action function *before* the responder.

    Args:
        action: A function with a similar signature to a resource responder
        method, taking (req, resp, params), where params includes values for
        URI template field names, if any. Hooks may also add pseudo-params
        of their own. For example:

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
                    if hasattr(responder, '__call__'):
                        # This pattern is necessary to capture the current
                        # value of responder in the do_before_all closure;
                        # otherwise, they will capture the same responder
                        # variable that is shared between iterations of the
                        # for loop, above.
                        def let(responder=responder):
                            @wraps(responder)
                            def do_before_all(self, req, resp, **kwargs):
                                action(req, resp, kwargs)
                                responder(self, req, resp, **kwargs)

                            api_helpers._propagate_argspec(
                                do_before_all,
                                responder)

                            setattr(resource, responder_name, do_before_all)

                        let()

            return resource

        else:
            responder = responder_or_resource

            @wraps(responder)
            def do_before_one(self, req, resp, **kwargs):
                action(req, resp, kwargs)
                responder(self, req, resp, **kwargs)

            api_helpers._propagate_argspec(do_before_one, responder)

            return do_before_one

    return _before


def after(action):
    """Decorator to execute the given action function *after* the responder.

    Args:
        action: A function with a similar signature to a resource responder
            method, taking (req, resp).

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
                    if hasattr(responder, '__call__'):
                        def let(responder=responder):
                            @wraps(responder)
                            def do_after_all(self, req, resp, **kwargs):
                                responder(self, req, resp, **kwargs)
                                action(req, resp)

                            api_helpers._propagate_argspec(
                                do_after_all,
                                responder)

                            setattr(resource, responder_name, do_after_all)

                        let()

            return resource

        else:
            responder = responder_or_resource

            @wraps(responder)
            def do_after_one(self, req, resp, **kwargs):
                responder(self, req, resp, **kwargs)
                action(req, resp)

            api_helpers._propagate_argspec(do_after_one, responder)

            return do_after_one

    return _after
