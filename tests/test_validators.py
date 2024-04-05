import typing

try:
    import jsonschema
except ImportError:
    jsonschema = None
try:
    import jsonschema_rs
except ImportError:
    jsonschema_rs = None
import pytest

import falcon
from falcon import testing
from falcon.media import validators

from _util import create_app, disable_asgi_non_coroutine_wrapping  # NOQA


# # NOTE(kgriffs): Default to None if missing. We do it like this, here, instead
# #   of in the body of the except statement, above, to avoid flake8 import
# #   ordering errors.
# jsonschema = globals().get('_jsonschema')


_VALID_MEDIA = {'message': 'something'}
_INVALID_MEDIA: typing.Dict[str, str] = {}


_TEST_SCHEMA = {
    'type': 'object',
    'properies': {
        'message': {
            'type': 'string',
        },
    },
    'required': ['message'],
}


@pytest.fixture(
    params=[
        pytest.param(
            'jsonschema',
            marks=pytest.mark.skipif(
                jsonschema is None, reason='jsonschema dependency not found'
            ),
        ),
        pytest.param(
            'jsonschema_rs',
            marks=pytest.mark.skipif(
                jsonschema_rs is None, reason='jsonschema_rs dependency not found'
            ),
        ),
    ]
)
def resources(request):
    if request.param == 'jsonschema':
        validate = validators.jsonschema.validate
    elif request.param == 'jsonschema_rs':
        validate = validators.jsonschema_rs.validate
    else:
        pytest.fail(request.param)

    class Resource:
        @validate(req_schema=_TEST_SCHEMA)
        def request_validated(self, req, resp):
            assert req.media is not None
            return resp

        @validate(resp_schema=_TEST_SCHEMA)
        def response_validated(self, req, resp):
            assert resp.media is not None
            return resp

        @validate(req_schema=_TEST_SCHEMA, resp_schema=_TEST_SCHEMA)
        def both_validated(self, req, resp):
            assert req.media is not None
            assert resp.media is not None
            return req, resp

        @validate(req_schema=_TEST_SCHEMA, resp_schema=_TEST_SCHEMA)
        def on_put(self, req, resp):
            assert req.media is not None
            resp.media = _VALID_MEDIA

    class ResourceAsync:
        @validate(req_schema=_TEST_SCHEMA)
        async def request_validated(self, req, resp):
            # NOTE(kgriffs): Verify that we can await req.get_media() multiple times
            for i in range(3):
                m = await req.get_media()
                assert m == _VALID_MEDIA

            assert m is not None
            return resp

        @validate(resp_schema=_TEST_SCHEMA)
        async def response_validated(self, req, resp):
            assert resp.media is not None
            return resp

        @validate(req_schema=_TEST_SCHEMA, resp_schema=_TEST_SCHEMA)
        async def both_validated(self, req, resp):
            m = await req.get_media()
            assert m is not None

            assert resp.media is not None

            return req, resp

        @validate(req_schema=_TEST_SCHEMA, resp_schema=_TEST_SCHEMA)
        async def on_put(self, req, resp):
            m = await req.get_media()
            assert m is not None
            resp.media = _VALID_MEDIA

    return Resource, ResourceAsync


class _MockReq:
    def __init__(self, valid=True):
        self.media = _VALID_MEDIA if valid else {}


class _MockReqAsync:
    def __init__(self, valid=True):
        self._media = _VALID_MEDIA if valid else {}

    async def get_media(self):
        return self._media


def MockReq(asgi, valid=True):
    return _MockReqAsync(valid) if asgi else _MockReq(valid)


class MockResp:
    def __init__(self, valid=True):
        self.media = _VALID_MEDIA if valid else {}


def call_method(resources, asgi, method_name, *args):
    resource = resources[1]() if asgi else resources[0]()

    if asgi:
        return falcon.async_to_sync(getattr(resource, method_name), *args)

    return getattr(resource, method_name)(*args)


def test_req_schema_validation_success(asgi, resources):
    data = MockResp()
    assert (
        call_method(resources, asgi, 'request_validated', MockReq(asgi), data) is data
    )


@pytest.mark.parametrize(
    'exception_cls', [falcon.HTTPBadRequest, falcon.MediaValidationError]
)
def test_req_schema_validation_failure(asgi, exception_cls, resources):
    with pytest.raises(exception_cls) as excinfo:
        call_method(resources, asgi, 'request_validated', MockReq(asgi, False), None)

    desc = excinfo.value.description.replace('"', "'")
    assert desc == "'message' is a required property"


def test_resp_schema_validation_success(asgi, resources):
    data = MockResp()
    assert (
        call_method(resources, asgi, 'response_validated', MockReq(asgi), data) is data
    )


def test_resp_schema_validation_failure(asgi, resources):
    with pytest.raises(falcon.HTTPInternalServerError) as excinfo:
        call_method(
            resources, asgi, 'response_validated', MockReq(asgi), MockResp(False)
        )

    assert excinfo.value.title == 'Response data failed validation'


def test_both_schemas_validation_success(asgi, resources):
    req = MockReq(asgi)
    resp = MockResp()

    result = call_method(resources, asgi, 'both_validated', req, resp)

    assert result[0] is req
    assert result[1] is resp

    client = testing.TestClient(create_app(asgi))
    resource = resources[1]() if asgi else resources[0]()
    client.app.add_route('/test', resource)

    result = client.simulate_put('/test', json=_VALID_MEDIA)
    assert result.json == resp.media


def test_both_schemas_validation_failure(asgi, resources):
    bad_resp = MockResp(False)

    with pytest.raises(falcon.HTTPInternalServerError) as excinfo:
        call_method(resources, asgi, 'both_validated', MockReq(asgi), bad_resp)

    assert excinfo.value.title == 'Response data failed validation'

    with pytest.raises(falcon.HTTPBadRequest) as excinfo:
        call_method(resources, asgi, 'both_validated', MockReq(asgi, False), MockResp())

    assert excinfo.value.title == 'Request data failed validation'

    client = testing.TestClient(create_app(asgi))
    resource = resources[1]() if asgi else resources[0]()

    with disable_asgi_non_coroutine_wrapping():
        client.app.add_route('/test', resource)

    result = client.simulate_put('/test', json=_INVALID_MEDIA)
    assert result.status_code == 400
