try:
    import jsonschema
except ImportError:
    jsonschema = None

import pytest

import falcon
from falcon import testing
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
    @validators.jsonschema.validate(req_schema=basic_schema)
    def request_validated(self, req, resp):
        assert req.media is not None
        return resp

    @validators.jsonschema.validate(resp_schema=basic_schema)
    def response_validated(self, req, resp):
        assert resp.media is not None
        return resp

    @validators.jsonschema.validate(req_schema=basic_schema, resp_schema=basic_schema)
    def both_validated(self, req, resp):
        assert req.media is not None
        assert resp.media is not None
        return req, resp

    @validators.jsonschema.validate(req_schema=basic_schema, resp_schema=basic_schema)
    def on_put(self, req, resp):
        assert req.media is not None
        resp.media = GoodData.media


class GoodData(object):
    media = {'message': 'something'}


class BadData(object):
    media = {}


@skip_missing_dep
def test_req_schema_validation_success():
    data = GoodData()
    assert Resource().request_validated(GoodData(), data) is data


@skip_missing_dep
def test_req_schema_validation_failure():
    with pytest.raises(falcon.HTTPBadRequest) as excinfo:
        Resource().request_validated(BadData(), None)

    assert excinfo.value.description == '\'message\' is a required property'


@skip_missing_dep
def test_resp_schema_validation_success():
    data = GoodData()
    assert Resource().response_validated(GoodData(), data) is data


@skip_missing_dep
def test_resp_schema_validation_failure():
    with pytest.raises(falcon.HTTPInternalServerError) as excinfo:
        Resource().response_validated(GoodData(), BadData())

    assert excinfo.value.title == 'Response data failed validation'


@skip_missing_dep
def test_both_schemas_validation_success():
    req_data = GoodData()
    resp_data = GoodData()

    result = Resource().both_validated(req_data, resp_data)

    assert result[0] is req_data
    assert result[1] is resp_data

    client = testing.TestClient(falcon.API())
    client.app.add_route('/test', Resource())
    result = client.simulate_put('/test', json=GoodData.media)
    assert result.json == resp_data.media


@skip_missing_dep
def test_both_schemas_validation_failure():
    with pytest.raises(falcon.HTTPInternalServerError) as excinfo:
        Resource().both_validated(GoodData(), BadData())

    assert excinfo.value.title == 'Response data failed validation'

    with pytest.raises(falcon.HTTPBadRequest) as excinfo:
        Resource().both_validated(BadData(), GoodData())

    assert excinfo.value.title == 'Request data failed validation'

    client = testing.TestClient(falcon.API())
    client.app.add_route('/test', Resource())
    result = client.simulate_put('/test', json=BadData.media)
    assert result.status_code == 400
