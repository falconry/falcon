from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

import pytest

import falcon
import falcon.testing


@dataclass
class RichContext:
    userid: Optional[UUID] = None
    role: str = 'anonymous'


class FancyRequest(falcon.Request):
    context_type = RichContext


class FancyResponse(falcon.Response):
    context_type = RichContext


USERS = {
    'am9objoxMjM0': ('user', UUID('51e4b478-3825-4e46-9fd7-be7b61d616dc')),
    'dnl0YXM6MTIz': ('admin', UUID('5e50d2c4-1c52-42c7-b4c5-879d9bd390ee')),
}


def fancy_error_serializer(
    req: FancyRequest, resp: falcon.Response, ex: falcon.HTTPError
) -> None:
    resp.content_type = falcon.MEDIA_JSON
    resp.media = ex.to_dict()
    resp.media.update(fancy=True)


class AuthMiddlewareFancyRequest:
    def process_request(self, req: FancyRequest, resp: falcon.Response) -> None:
        if req.method == 'OPTIONS':
            return

        if req.auth:
            for key, user_role in USERS.items():
                if req.auth == f'Basic {key}':
                    req.context.role, req.context.userid = user_role
                    break
            else:
                raise falcon.HTTPUnauthorized()


class AuthMiddlewareFancyBoth:
    def process_request(self, req: FancyRequest, resp: FancyResponse) -> None:
        if req.method == 'OPTIONS':
            return

        if req.auth:
            for key, user_role in USERS.items():
                if req.auth == f'Basic {key}':
                    req.context.role, req.context.userid = user_role
                    break
            else:
                raise falcon.HTTPUnauthorized()


def sink_fancy_req(req: FancyRequest, resp: falcon.Response, **kwargs: Any) -> None:
    userid: Optional[str] = str(req.context.userid) if req.context.userid else None
    resp.media = {'role': req.context.role, 'userid': userid}
    if req.path == '/not-found':
        raise falcon.HTTPNotFound()


def sink_fancy_both(req: FancyRequest, resp: FancyResponse, **kwargs: Any) -> None:
    sink_fancy_req(req, resp, **kwargs)


def create_app_fancy_req() -> falcon.App:
    app = falcon.App(request_type=FancyRequest)
    app.add_middleware(AuthMiddlewareFancyRequest())
    app.add_sink(sink_fancy_req)
    app.set_error_serializer(fancy_error_serializer)
    return app


def create_app_fancy_both() -> falcon.App:
    app = falcon.App(request_type=FancyRequest, response_type=FancyResponse)
    app.add_middleware(AuthMiddlewareFancyBoth())
    app.add_sink(sink_fancy_both)
    app.set_error_serializer(fancy_error_serializer)
    return app


@pytest.mark.parametrize('create_app', [create_app_fancy_req, create_app_fancy_both])
def test_fancy_wsgi_app(create_app) -> None:
    client = falcon.testing.TestClient(create_app())

    result1 = client.get()
    assert result1.status_code == 200
    assert result1.json == {
        'role': 'anonymous',
        'userid': None,
    }

    result2 = client.get(headers={'Authorization': 'ApiKey 123'})
    assert result2.status_code == 401

    result3 = client.get(headers={'Authorization': 'Basic am9objoxMjM0'})
    assert result3.status_code == 200
    assert result3.json == {
        'role': 'user',
        'userid': '51e4b478-3825-4e46-9fd7-be7b61d616dc',
    }

    result4 = client.get('/not-found')
    assert result4.status_code == 404
    assert result4.json == {'fancy': True, 'title': '404 Not Found'}
