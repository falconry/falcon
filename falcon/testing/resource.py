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

"""Mock resource classes.

This module contains mock resource classes and associated hooks for use
in Falcon framework tests. The classes and hooks may be referenced
directly from the `testing` package::

    from falcon import testing

    resource = testing.SimpleTestResource()

"""

from json import dumps as json_dumps

import falcon


def capture_responder_args(req, resp, resource, params):
    """Before hook for capturing responder arguments.

    Adds the following attributes to the hooked responder's resource
    class:

        * captured_req
        * captured_resp
        * captured_kwargs
    """

    resource.captured_req = req
    resource.captured_resp = resp
    resource.captured_kwargs = params


def set_resp_defaults(req, resp, resource, params):
    """Before hook for setting default response properties."""

    if resource._default_status is not None:
        resp.status = resource._default_status

    if resource._default_body is not None:
        resp.body = resource._default_body

    if resource._default_headers is not None:
        resp.set_headers(resource._default_headers)


class SimpleTestResource(object):
    """Mock resource for functional testing of framework components.

    This class implements a simple test resource that can be extended
    as needed to test middleware, hooks, and the Falcon framework
    itself.

    Only noop ``on_get()`` and ``on_post()`` responders are implemented;
    when overriding these, or adding additional responders in child
    classes, they can be decorated with the
    :py:meth:`falcon.testing.capture_responder_args` hook in
    order to capture the *req*, *resp*, and *params* arguments that
    are passed to the responder. Responders may also be decorated with
    the :py:meth:`falcon.testing.set_resp_defaults` hook in order to
    set *resp* properties to default *status*, *body*, and *header*
    values.

    Keyword Arguments:
        status (str): Default status string to use in responses
        body (str): Default body string to use in responses
        json (JSON serializable): Default JSON document to use in responses.
            Will be serialized to a string and encoded as UTF-8. Either
            *json* or *body* may be specified, but not both.
        headers (dict): Default set of additional headers to include in
            responses

    Attributes:
        called (bool): Whether or not a req/resp was captured.
        captured_req (falcon.Request): The last Request object passed
            into any one of the responder methods.
        captured_resp (falcon.Response): The last Response object passed
            into any one of the responder methods.
        captured_kwargs (dict): The last dictionary of kwargs, beyond
            ``req`` and ``resp``, that were passed into any one of the
            responder methods.
    """

    def __init__(self, status=None, body=None, json=None, headers=None):
        self._default_status = status
        self._default_headers = headers

        if json is not None:
            if body is not None:
                msg = 'Either json or body may be specified, but not both'
                raise ValueError(msg)

            self._default_body = json_dumps(json, ensure_ascii=False)

        else:
            self._default_body = body

        self.captured_req = None
        self.captured_resp = None
        self.captured_kwargs = None

    @property
    def called(self):
        return self.captured_req is not None

    @falcon.before(capture_responder_args)
    @falcon.before(set_resp_defaults)
    def on_get(self, req, resp, **kwargs):
        pass

    @falcon.before(capture_responder_args)
    @falcon.before(set_resp_defaults)
    def on_post(self, req, resp, **kwargs):
        pass
