import sys

import pytest

import falcon
from falcon.media.validators import jsonschema

skip_py26 = pytest.mark.skipif(
    sys.version_info[:2] == (2, 6),
    reason='Minimum Python version for this feature is 2.7.x'
)

basic_schema = {
    'type': 'object',
    'properies': {
        'message': {
            'type': 'string',
        },
    },
    'required': ['message'],
}


class Resource(object):
    @jsonschema.validate(schema_request=basic_schema)
    def request_validated(self, req, resp):
        assert req.media is not None
        return resp

    @jsonschema.validate(schema_response=basic_schema)
    def response_validated(self, req, resp):
        assert req.media is not None
        return resp


class GoodData(object):
    media = {'message': 'something'}


class BadData(object):
    media = {}


@skip_py26
def test_jsonschema_request_validation_success():
    data = GoodData()
    assert Resource().request_validated(GoodData(), data) is data


@skip_py26
def test_jsonschema_request_validation_failure():
    with pytest.raises(falcon.HTTPBadRequest) as err:
        Resource().request_validated(BadData(), None)
        assert err.value.description == '\'message\' is a required property'


@skip_py26
def test_jsonschema_response_validation_success():
    data = GoodData()
    assert Resource().response_validated(GoodData(), data) is data


@skip_py26
def test_jsonschema_response_validation_failure():
    with pytest.raises(falcon.HTTPInternalServerError) as err:
        Resource().response_validated(GoodData(), BadData())
        assert err.title == 'Response data failed validation'
