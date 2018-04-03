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


class SampleResource(object):
    @validators.jsonschema.validate(basic_schema)
    def on_get(self, req, resp):
        assert req.media is not None


class RequestStub(object):
    media = {'message': 'something'}


@skip_missing_dep
def test_jsonschema_validation_success():
    req = RequestStub()

    res = SampleResource()
    assert res.on_get(req, None) is None


@skip_missing_dep
def test_jsonschema_validation_failure():
    req = RequestStub()
    req.media = {}

    res = SampleResource()
    with pytest.raises(falcon.HTTPBadRequest) as err:
        res.on_get(req, None)

    assert err.value.description == '\'message\' is a required property'
