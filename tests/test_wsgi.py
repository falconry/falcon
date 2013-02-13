import sys

import testtools
from testtools.matchers import Equals, MatchesRegex

import falcon
import falcon.testing as testing


def _is_iterable(thing):
    try:
        for i in thing:
            break

        return True
    except:
        return False


class TestWsgi(testtools.TestCase):

    def test_srmock(self):
        mock = testing.StartResponseMock()
        mock(falcon.HTTP_200, ())

        self.assertEqual(falcon.HTTP_200, mock.status)
        self.assertEqual(None, mock.exc_info)

        mock = testing.StartResponseMock()
        exc_info = sys.exc_info()
        mock(falcon.HTTP_200, (), exc_info)

        self.assertEqual(exc_info, mock.exc_info)

    def test_pep3333(self):
        api = falcon.API()
        mock = testing.StartResponseMock()

        # Simulate a web request (normally done though a WSGI server)
        response = api(testing.create_environ(), mock)

        # Verify that the response is iterable
        self.assertTrue(_is_iterable(response))

        # Make sure start_response was passed a valid status string
        self.assertIs(mock.call_count, 1)
        self.assertTrue(isinstance(mock.status, str))
        self.assertThat(mock.status, MatchesRegex('^\d+[a-zA-Z\s]+$'))

        # Verify headers is a list of tuples, each containing a pair of strings
        self.assertTrue(isinstance(mock.headers, list))
        if len(mock.headers) != 0:
            header = mock.headers[0]
            self.assertTrue(isinstance(header, tuple))
            self.assertThat(len(header), Equals(2))
            self.assertTrue(isinstance(header[0], str))
            self.assertTrue(isinstance(header[1], str))
