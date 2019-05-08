import asyncio
import os

try:
    import jsonschema as _jsonschema  # NOQA
except ImportError:
    pass
import pytest

import falcon
from falcon import testing
from falcon.media import validators
from ._util import create_app


# NOTE(kgriffs): Default to None if missing. We do it like this, here, instead
#   of in the body of the except statement, above, to avoid flake8 import
#   ordering errors.
jsonschema = globals().get('_jsonschema')


_VALID_MEDIA = {'message': 'something'}
_INVALID_MEDIA = {}


_TEST_SCHEMA = {
    'type': 'object',
    'properies': {
        'message': {
            'type': 'string',
        },
    },
    'required': ['message'],
}


skip_missing_dep = pytest.mark.skipif(
    jsonschema is None,
    reason='jsonschema dependency not found'
)


class Resource:
    @validators.jsonschema.validate(req_schema=_TEST_SCHEMA)
    def request_validated(self, req, resp):
        assert req.media is not None
        return resp

    @validators.jsonschema.validate(resp_schema=_TEST_SCHEMA)
    def response_validated(self, req, resp):
        assert resp.media is not None
        return resp

    @validators.jsonschema.validate(req_schema=_TEST_SCHEMA, resp_schema=_TEST_SCHEMA)
    def both_validated(self, req, resp):
        assert req.media is not None
        assert resp.media is not None
        return req, resp

    @validators.jsonschema.validate(req_schema=_TEST_SCHEMA, resp_schema=_TEST_SCHEMA)
    def on_put(self, req, resp):
        assert req.media is not None
        resp.media = _VALID_MEDIA


class ResourceAsync:
    @validators.jsonschema.validate(req_schema=_TEST_SCHEMA)
    async def request_validated(self, req, resp):
        assert req.media is not None
        return resp

    @validators.jsonschema.validate(resp_schema=_TEST_SCHEMA)
    async def response_validated(self, req, resp):
        assert resp.media is not None
        return resp

    @validators.jsonschema.validate(req_schema=_TEST_SCHEMA, resp_schema=_TEST_SCHEMA)
    async def both_validated(self, req, resp):
        assert req.media is not None
        assert resp.media is not None
        return req, resp

    @validators.jsonschema.validate(req_schema=_TEST_SCHEMA, resp_schema=_TEST_SCHEMA)
    async def on_put(self, req, resp):
        assert req.media is not None
        resp.media = _VALID_MEDIA


class MockReq:
    def __init__(self, asgi, valid=True):
        media = _VALID_MEDIA if valid else {}

        if asgi:
            self._media = media
            self.media = self._media_async
        else:
            self.media = media

    @property
    async def _media_async(self):
        return self._media


class MockResp:
    def __init__(self, valid=True):
        self.media = _VALID_MEDIA if valid else {}


def call_method(asgi, method_name, *args):
    resource = ResourceAsync() if asgi else Resource()

    result = getattr(resource, method_name)(*args)
    if asgi:
        return asyncio.get_event_loop().run_until_complete(result)
    else:
        return result


@skip_missing_dep
def test_req_schema_validation_success(asgi):
    data = MockResp()
    assert call_method(asgi, 'request_validated', MockReq(asgi), data) is data


@skip_missing_dep
def test_req_schema_validation_failure(asgi):
    with pytest.raises(falcon.HTTPBadRequest) as excinfo:
        call_method(asgi, 'request_validated', MockReq(asgi, False), None)

    assert excinfo.value.description == "'message' is a required property"


@skip_missing_dep
def test_resp_schema_validation_success(asgi):
    data = MockResp()
    assert call_method(asgi, 'response_validated', MockReq(asgi), data) is data


@skip_missing_dep
def test_resp_schema_validation_failure(asgi):
    with pytest.raises(falcon.HTTPInternalServerError) as excinfo:
        call_method(asgi, 'response_validated', MockReq(asgi), MockResp(False))

    assert excinfo.value.title == 'Response data failed validation'


@skip_missing_dep
def test_both_schemas_validation_success(asgi):
    req = MockReq(asgi)
    resp = MockResp()

    result = call_method(asgi, 'both_validated', req, resp)

    assert result[0] is req
    assert result[1] is resp

    client = testing.TestClient(create_app(asgi))
    resource = ResourceAsync() if asgi else Resource()
    client.app.add_route('/test', resource)

    result = client.simulate_put('/test', json=_VALID_MEDIA)
    assert result.json == resp.media


@skip_missing_dep
def test_both_schemas_validation_failure(asgi):
    bad_resp = MockResp(False)

    with pytest.raises(falcon.HTTPInternalServerError) as excinfo:
        call_method(asgi, 'both_validated', MockReq(asgi), bad_resp)

    assert excinfo.value.title == 'Response data failed validation'

    with pytest.raises(falcon.HTTPBadRequest) as excinfo:
        call_method(asgi, 'both_validated', MockReq(asgi, False), MockResp())

    assert excinfo.value.title == 'Request data failed validation'

    client = testing.TestClient(create_app(asgi))
    resource = ResourceAsync() if asgi else Resource()

    should_wrap = 'FALCON_ASGI_WRAP_RESPONDERS' in os.environ

    if should_wrap:
        del os.environ['FALCON_ASGI_WRAP_RESPONDERS']
    client.app.add_route('/test', resource)
    if should_wrap:
        os.environ['FALCON_ASGI_WRAP_RESPONDERS'] = 'y'

    result = client.simulate_put('/test', json=_INVALID_MEDIA)
    assert result.status_code == 400
