from unittest.mock import Mock

import falcon
from examples.things import app, things, ThingsResource

def test_app():
    assert app
    (resource, method_map, params, uri_template) = app._router.find('/things')
    assert resource is things


def test_things():
    assert isinstance(things, ThingsResource)


def test_ThingsResource_on_get():
    test_thing = ThingsResource()
    mock_response = Mock()
    test_thing.on_get(None, mock_response)
    assert mock_response.status == falcon.HTTP_200
    assert len(mock_response.body) > 10
