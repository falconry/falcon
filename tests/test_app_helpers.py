import pytest

from falcon import HTTPNotFound
from falcon import ResponseOptions
from falcon.app_helpers import default_serialize_error
from falcon.media import BaseHandler
from falcon.media import Handlers
from falcon.request import Request
from falcon.response import Response
from falcon.testing import create_environ

JSON_CONTENT = b'{"title": "404 Not Found"}'
JSON = ('application/json', 'application/json', JSON_CONTENT)
XML = (
    'application/xml',
    'application/xml',
    (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<error><title>404 Not Found</title></error>'
    ),
)
CUSTOM_JSON = ('custom/any+json', 'application/json', JSON_CONTENT)

CUSTOM_XML = (
    'custom/any+xml',
    'application/xml',
    (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<error><title>404 Not Found</title></error>'
    ),
)

YAML = (
    'application/yaml',
    'application/yaml',
    (b'error:\n' b'    title: 404 Not Found'),
)


class FakeYamlMediaHandler(BaseHandler):
    def serialize(self, media: object, content_type: str) -> bytes:
        return b'error:\n' b'    title: 404 Not Found'


class TestDefaultSerializeError:
    def test_if_no_content_type_and_accept_fall_back_to_json(self) -> None:
        response = Response()
        default_serialize_error(
            Request(env=(create_environ())),
            response,
            HTTPNotFound(),
        )
        assert response.content_type == 'application/json'
        assert response.headers['vary'] == 'Accept'
        assert response.data == JSON_CONTENT

    @pytest.mark.parametrize(
        'accept, content_type, data',
        (
            JSON,
            XML,
            CUSTOM_JSON,
            CUSTOM_XML,
            YAML,
        ),
    )
    def test_serializes_error_to_preferred_by_sender(
        self, accept, content_type, data
    ) -> None:
        handlers = Handlers()
        handlers['application/yaml'] = FakeYamlMediaHandler()
        options = ResponseOptions()
        options.media_handlers = handlers
        response = Response(options=options)
        default_serialize_error(
            Request(env=(create_environ(headers={'accept': accept}))),
            response,
            HTTPNotFound(),
        )
        assert response.content_type == content_type
        assert response.headers['vary'] == 'Accept'
        assert response.data == data
