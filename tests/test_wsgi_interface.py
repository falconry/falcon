import re
import sys

import pytest

import falcon
import falcon.testing as testing


@pytest.fixture
def app():
    return falcon.API()


@pytest.fixture
def builder_app():
    return falcon.APIBuilder().build()


class TestWSGIInterface(object):

    def test_srmock(self):
        mock = testing.StartResponseMock()
        mock(falcon.HTTP_200, ())

        assert mock.status == falcon.HTTP_200
        assert mock.exc_info is None

        mock = testing.StartResponseMock()
        exc_info = sys.exc_info()
        mock(falcon.HTTP_200, (), exc_info)

        assert mock.exc_info == exc_info

    @pytest.mark.parametrize('app', [
        'app',
        'builder_app'
    ], indirect=True)
    def test_pep3333(self, app):
        mock = testing.StartResponseMock()

        # Simulate a web request (normally done though a WSGI server)
        response = app(testing.create_environ(), mock)

        # Verify that the response is iterable
        assert _is_iterable(response)

        # Make sure start_response was passed a valid status string
        assert mock.call_count == 1
        assert isinstance(mock.status, str)
        assert re.match(r'^\d+[a-zA-Z\s]+$', mock.status)

        # Verify headers is a list of tuples, each containing a pair of strings
        assert isinstance(mock.headers, list)
        if len(mock.headers) != 0:
            header = mock.headers[0]
            assert isinstance(header, tuple)
            assert len(header) == 2
            assert isinstance(header[0], str)
            assert isinstance(header[1], str)


def _is_iterable(thing):
    try:
        for i in thing:
            break

        return True
    except TypeError:
        return False
