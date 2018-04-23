try:
    import jsonschema
except ImportError:
    jsonschema = None

import pytest

import falcon
from falcon.media import validators

basic_schema = {
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


class Resource(object):
    @validators.jsonschema.validate(schema_request=basic_schema)
    def request_validated(self, req, resp):
        assert req.media is not None
        return resp

    @validators.jsonschema.validate(schema_response=basic_schema)
    def response_validated(self, req, resp):
        assert req.media is not None
        return resp


class GoodData(object):
    media = {'message': 'something'}


class BadData(object):
    media = {}


@skip_missing_dep
def test_jsonschema_request_validation_success():
    data = GoodData()
    assert Resource().request_validated(GoodData(), data) is data


@skip_missing_dep
def test_jsonschema_request_validation_failure():
    with pytest.raises(falcon.HTTPBadRequest) as err:
        Resource().request_validated(BadData(), None)
        assert err.value.description == '\'message\' is a required property'


@skip_missing_dep
def test_jsonschema_response_validation_success():
    data = GoodData()
    assert Resource().response_validated(GoodData(), data) is data


@skip_missing_dep
def test_jsonschema_response_validation_failure():
    with pytest.raises(falcon.HTTPInternalServerError) as err:
        Resource().response_validated(GoodData(), BadData())
        assert err.title == 'Response data failed validation'
