from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import falcon
import falcon.asgi
import falcon.testing


@dataclass
class RichContext:
    userid: UUID | None = None
    role: str = 'anonymous'
    comment: str = 'no comment'


class FancyRequest(falcon.Request):
    context_type = RichContext


class FancyResponse(falcon.Response):
    context_type = RichContext

    # NOTE(vytas): the `type: ignore` exemption is currently required if it is
    #   desirable to actually check typing of context attributes. See also:
    #   https://falcon.readthedocs.io/en/latest/api/typing.html#known-limitations
    context: RichContext  # type: ignore[assignment]


class FancyAsyncRequest(falcon.asgi.Request):
    context_type = RichContext


class FancyAsyncResponse(falcon.asgi.Response):
    context_type = RichContext

    # NOTE(vytas): the `type: ignore` exemption is currently required if it is
    #   desirable to actually check typing of context attributes. See also:
    #   https://falcon.readthedocs.io/en/latest/api/typing.html#known-limitations
    context: RichContext  # type: ignore[assignment]


USERS = {
    'am9objoxMjM0': ('user', UUID('51e4b478-3825-4e46-9fd7-be7b61d616dc')),
    'dnl0YXM6MTIz': ('admin', UUID('5e50d2c4-1c52-42c7-b4c5-879d9bd390ee')),
}


def fancy_error_serializer(
    req: FancyRequest, resp: falcon.Response, ex: falcon.HTTPError
) -> None:
    resp.content_type = falcon.MEDIA_JSON
    resp.media = ex.to_dict()
    resp.media.update(fancy=True, asgi=False)


def fancy_asgi_error_serializer(
    req: FancyAsyncRequest, resp: falcon.asgi.Response, ex: falcon.HTTPError
) -> None:
    resp.content_type = falcon.MEDIA_JSON
    resp.media = ex.to_dict()
    resp.media.update(fancy=True, asgi=True)


def _process_auth(req: falcon.Request, resp: falcon.Response) -> None:
    if req.method == 'OPTIONS':
        return

    if req.auth:
        for key, user_role in USERS.items():
            if req.auth == f'Basic {key}':
                req.context.role, req.context.userid = user_role
                break
        else:
            raise falcon.HTTPUnauthorized()


class AuthMiddlewareFancyRequest:
    def process_request(self, req: FancyRequest, resp: falcon.Response) -> None:
        _process_auth(req, resp)

    async def process_request_async(
        self, req: FancyAsyncRequest, resp: falcon.asgi.Response
    ) -> None:
        _process_auth(req, resp)


class AuthMiddlewareFancyBoth:
    def process_request(self, req: FancyRequest, resp: FancyResponse) -> None:
        _process_auth(req, resp)

        # NOTE(vytas): Unlike req.context, resp.context.comment is type checked,
        #   try misspelling it or using with an incompatible type.
        resp.context.comment = 'fancy req/resp'

    async def process_request_async(
        self, req: FancyAsyncRequest, resp: FancyAsyncResponse
    ) -> None:
        _process_auth(req, resp)
        resp.context.comment = 'fancy req/resp'


def _sink_impl(req: falcon.Request, resp: falcon.Response) -> None:
    userid: str | None = str(req.context.userid) if req.context.userid else None
    resp.media = {'role': req.context.role, 'userid': userid}
    if req.path == '/not-found':
        raise falcon.HTTPNotFound()


def sink_fancy_req(req: FancyRequest, resp: falcon.Response, **kwargs: Any) -> None:
    _sink_impl(req, resp)


def sink_fancy_both(req: FancyRequest, resp: FancyResponse, **kwargs: Any) -> None:
    _sink_impl(req, resp)
    resp.context.comment += ' (sink)'
    resp.media.update(comment=resp.context.comment)


async def sink_fancy_async_req(
    req: FancyAsyncRequest, resp: falcon.asgi.Response | None, **kwargs: Any
) -> None:
    if resp is not None:
        _sink_impl(req, resp)


async def sink_fancy_async_both(
    req: FancyAsyncRequest, resp: FancyAsyncResponse | None, **kwargs: Any
) -> None:
    if resp is not None:
        _sink_impl(req, resp)
        resp.context.comment += ' (sink)'
        resp.media.update(comment=resp.context.comment)


# NOTE(vytas): We don't use fixtures here because that is hard to marry to strict
#   type checking, Mypy complains that "Untyped decorator makes function untyped".
def test_app_fancy_req() -> None:
    app = falcon.App(request_type=FancyRequest)
    app.add_middleware(AuthMiddlewareFancyRequest())
    app.add_sink(sink_fancy_req)
    app.set_error_serializer(fancy_error_serializer)

    _exercise_app(app)


def test_app_fancy_both() -> None:
    app = falcon.App(request_type=FancyRequest, response_type=FancyResponse)
    app.add_middleware(AuthMiddlewareFancyBoth())
    app.add_sink(sink_fancy_both)
    app.set_error_serializer(fancy_error_serializer)

    _exercise_app(app)


def test_app_fancy_async_req() -> None:
    app = falcon.asgi.App(request_type=FancyAsyncRequest)
    app.add_middleware(AuthMiddlewareFancyRequest())
    app.add_sink(sink_fancy_async_req)
    app.set_error_serializer(fancy_asgi_error_serializer)

    _exercise_app(app)


def test_app_fancy_async_both() -> None:
    app = falcon.asgi.App(
        request_type=FancyAsyncRequest, response_type=FancyAsyncResponse
    )
    app.add_middleware(AuthMiddlewareFancyBoth())
    app.add_sink(sink_fancy_async_both)
    app.set_error_serializer(fancy_asgi_error_serializer)

    _exercise_app(app)


def _exercise_app(app: falcon.App[Any, Any]) -> None:
    client = falcon.testing.TestClient(app)

    result1 = client.get()
    assert result1.status_code == 200
    assert result1.json in (
        {
            'role': 'anonymous',
            'userid': None,
        },
        {
            'comment': 'fancy req/resp (sink)',
            'role': 'anonymous',
            'userid': None,
        },
    )

    result2 = client.get(headers={'Authorization': 'ApiKey 123'})
    assert result2.status_code == 401

    result3 = client.get(headers={'Authorization': 'Basic am9objoxMjM0'})
    assert result3.status_code == 200
    assert result3.json in (
        {
            'role': 'user',
            'userid': '51e4b478-3825-4e46-9fd7-be7b61d616dc',
        },
        {
            'comment': 'fancy req/resp (sink)',
            'role': 'user',
            'userid': '51e4b478-3825-4e46-9fd7-be7b61d616dc',
        },
    )

    result4 = client.get('/not-found')
    assert result4.status_code == 404
    assert result4.json == {
        'asgi': isinstance(client.app, falcon.asgi.App),
        'fancy': True,
        'title': '404 Not Found',
    }
