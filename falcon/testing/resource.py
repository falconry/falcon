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

from __future__ import annotations

from json import dumps as json_dumps
import typing

import falcon

if typing.TYPE_CHECKING:  # pragma: no cover
    from falcon import app as wsgi
    from falcon._typing import HeaderArg
    from falcon._typing import Resource
    from falcon.asgi import app as asgi


def capture_responder_args(
    req: wsgi.Request,
    resp: wsgi.Response,
    resource: object,
    params: typing.Mapping[str, str],
) -> None:
    """Before hook for capturing responder arguments.

    Adds the following attributes to the hooked responder's resource
    class:

        * `captured_req`
        * `captured_resp`
        * `captured_kwargs`

    In addition, if the capture-req-body-bytes header is present in the
    request, the following attribute is added:

        * `captured_req_body`

    Including the capture-req-media header in the request (set to any
    value) will add the following attribute:

        * `capture-req-media`
    """

    simple_resource = typing.cast(SimpleTestResource, resource)
    simple_resource.captured_req = req
    simple_resource.captured_resp = resp
    simple_resource.captured_kwargs = params

    simple_resource.captured_req_media = None
    simple_resource.captured_req_body = None

    num_bytes = req.get_header('capture-req-body-bytes')
    if num_bytes:
        simple_resource.captured_req_body = req.stream.read(int(num_bytes))
    elif req.get_header('capture-req-media'):
        simple_resource.captured_req_media = req.get_media()


async def capture_responder_args_async(
    req: asgi.Request,
    resp: asgi.Response,
    resource: Resource,
    params: typing.Mapping[str, str],
) -> None:
    """Before hook for capturing responder arguments.

    An asynchronous version of :meth:`~falcon.testing.capture_responder_args`.
    """

    simple_resource = typing.cast(SimpleTestResource, resource)
    simple_resource.captured_req = req
    simple_resource.captured_resp = resp
    simple_resource.captured_kwargs = params

    simple_resource.captured_req_media = None
    simple_resource.captured_req_body = None

    num_bytes = req.get_header('capture-req-body-bytes')
    if num_bytes:
        simple_resource.captured_req_body = await req.stream.read(int(num_bytes))
    elif req.get_header('capture-req-media'):
        simple_resource.captured_req_media = await req.get_media()


def set_resp_defaults(
    req: wsgi.Request,
    resp: wsgi.Response,
    resource: Resource,
    params: typing.Mapping[str, str],
) -> None:
    """Before hook for setting default response properties.

    This hook simply sets the the response body, status,
    and headers to the `_default_status`,
    `_default_body`, and `_default_headers` attributes
    that are assumed to be defined on the resource
    object.
    """
    simple_resource = typing.cast(SimpleTestResource, resource)
    if simple_resource._default_status is not None:
        resp.status = simple_resource._default_status

    if simple_resource._default_body is not None:
        resp.text = simple_resource._default_body

    if simple_resource._default_headers is not None:
        resp.set_headers(simple_resource._default_headers)


async def set_resp_defaults_async(
    req: asgi.Request,
    resp: asgi.Response,
    resource: Resource,
    params: typing.Mapping[str, str],
) -> None:
    """Wrap :meth:`~falcon.testing.set_resp_defaults` in a coroutine."""
    set_resp_defaults(req, resp, resource, params)


class SimpleTestResource:
    """Mock resource for functional testing of framework components.

    This class implements a simple test resource that can be extended
    as needed to test middleware, hooks, and the Falcon framework
    itself.

    Only noop ``on_get()`` and ``on_post()`` responders are implemented;
    when overriding these, or adding additional responders in child
    classes, they can be decorated with the
    :meth:`falcon.testing.capture_responder_args` hook in
    order to capture the *req*, *resp*, and *params* arguments that
    are passed to the responder. Responders may also be decorated with
    the :meth:`falcon.testing.set_resp_defaults` hook in order to
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
    """

    captured_req: typing.Optional[typing.Union[wsgi.Request, asgi.Request]]
    """The last Request object passed into any one of the responder methods."""
    captured_resp: typing.Optional[typing.Union[wsgi.Response, asgi.Response]]
    """The last Response object passed into any one of the responder methods."""

    captured_kwargs: typing.Optional[typing.Any]
    """The last dictionary of kwargs, beyond ``req`` and ``resp``, that were
    passed into any one of the responder methods."""

    captured_req_media: typing.Optional[typing.Any]
    """The last Request media provided to any one of the responder methods.

    This value is only captured when the ``'capture-req-media'`` header is
    set on the request.
    """
    captured_req_body: typing.Optional[bytes]
    """The last Request body provided to any one of the responder methods.

    This value is only captured when the ``'capture-req-body-bytes'`` header is
    set on the request. The value of the header is the number of bytes to read.
    """

    def __init__(
        self,
        status: typing.Optional[str] = None,
        body: typing.Optional[str] = None,
        json: typing.Optional[dict[str, str]] = None,
        headers: typing.Optional[HeaderArg] = None,
    ) -> None:
        self._default_status = status
        self._default_headers = headers

        if json is not None:
            if body is not None:
                msg = 'Either json or body may be specified, but not both'
                raise ValueError(msg)

            self._default_body: typing.Optional[str] = json_dumps(
                json, ensure_ascii=False
            )

        else:
            self._default_body = body

        self.captured_req = None
        self.captured_resp = None
        self.captured_kwargs = None
        self.captured_req_media = None
        self.captured_req_body = None

    @property
    def called(self) -> bool:
        """Whether or not a req/resp was captured."""
        return self.captured_req is not None

    @falcon.before(capture_responder_args)
    @falcon.before(set_resp_defaults)
    def on_get(
        self, req: wsgi.Request, resp: wsgi.Response, **kwargs: typing.Any
    ) -> None:
        pass

    @falcon.before(capture_responder_args)
    @falcon.before(set_resp_defaults)
    def on_post(
        self, req: wsgi.Request, resp: wsgi.Response, **kwargs: typing.Any
    ) -> None:
        pass


class SimpleTestResourceAsync(SimpleTestResource):
    """Mock resource for functional testing of ASGI framework components.

    This class implements a simple test resource that can be extended
    as needed to test middleware, hooks, and the Falcon framework
    itself. It is identical to SimpleTestResource, except that it implements
    asynchronous responders for use with the ASGI interface.

    Only noop ``on_get()`` and ``on_post()`` responders are implemented;
    when overriding these, or adding additional responders in child
    classes, they can be decorated with the
    :meth:`falcon.testing.capture_responder_args` hook in
    order to capture the *req*, *resp*, and *params* arguments that
    are passed to the responder. Responders may also be decorated with
    the :meth:`falcon.testing.set_resp_defaults` hook in order to
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
    """

    @falcon.before(capture_responder_args_async)
    @falcon.before(set_resp_defaults_async)
    async def on_get(  # type: ignore[override]
        self, req: asgi.Request, resp: asgi.Response, **kwargs: typing.Any
    ) -> None:
        pass

    @falcon.before(capture_responder_args_async)
    @falcon.before(set_resp_defaults_async)
    async def on_post(  # type: ignore[override]
        self, req: asgi.Request, resp: asgi.Response, **kwargs: typing.Any
    ) -> None:
        pass
