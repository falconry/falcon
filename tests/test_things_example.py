from unittest.mock import Mock

from examples.things import app, things, ThingsResource
import falcon


def test_app():
    assert app
    resource, *_ = app._router.find('/things')
    assert resource is things


def test_things():
    assert isinstance(things, ThingsResource)


def test_ThingsResource_on_get():
    test_thing = ThingsResource()
    mock_response = Mock()
    test_thing.on_get(None, mock_response)
    assert mock_response.status == falcon.HTTP_200
    assert mock_response.body == (
        '\nTwo things awe me most, the starry sky above me and the moral law within me.'
        '\n    ~ Immanuel Kant\n'
    )
