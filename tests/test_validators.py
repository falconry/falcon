import pytest

import falcon
from falcon.media.validators import jsonschema

basic_schema = {
    'type': 'object',
    'properies': {
        'message': {
            'type': 'string',
        },
    },
    'required': ['message'],
}


class SampleResource(object):
    @jsonschema.validate(basic_schema)
    def on_get(self, req, resp):
        assert req.media is not None


class RequestStub(object):
    media = {'message': 'something'}


def test_jsonschema_validation_success():
    req = RequestStub()

    res = SampleResource()
    assert res.on_get(req, None) is None


def test_jsonschema_validation_failure():
    req = RequestStub()
    req.media = {}

    res = SampleResource()
    with pytest.raises(falcon.HTTPBadRequest) as err:
        res.on_get(req, None)

    assert err.value.description == '\'message\' is a required property'
