import pytest

from falcon import HTTPNotFound
from falcon.app_helpers import default_serialize_error
from falcon.request import Request
from falcon.response import Response
from falcon.testing import create_environ

JSON = ('application/json', 'application/json', b'{"title": "404 Not Found"}')
XML = (
    'application/xml',
    'application/xml',
    (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<error><title>404 Not Found</title></error>'
    ),
)
CUSTOM_JSON = ('custom/any+json', 'application/json', b'{"title": "404 Not Found"}')

CUSTOM_XML = (
    'custom/any+xml',
    'application/xml',
    (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<error><title>404 Not Found</title></error>'
    ),
)


class TestDefaultSerializeError:
    @pytest.mark.parametrize(
        'accept, content_type, data',
        (
            JSON,
            XML,
            CUSTOM_JSON,
            CUSTOM_XML,
        ),
    )
    def test_serializes_error_to_preffered_by_sender(
        self, accept, content_type, data
    ) -> None:
        response = Response()
        default_serialize_error(
            Request(env=(create_environ(headers={'accept': accept}))),
            response,
            HTTPNotFound(),
        )
        assert response.content_type == content_type
        assert response.headers['vary'] == 'Accept'
        assert response.data == data
