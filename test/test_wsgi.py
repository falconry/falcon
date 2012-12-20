import testtools
from testtools.matchers import Equals, MatchesRegex

import falcon
import test.helpers as helpers

def _is_iterable(thing):
    try:
        for i in thing:
            break

        return True
    except:
        return False

class TestWsgi(testtools.TestCase):

    def test_pep333(self):
        api = falcon.Api()
        mock = helpers.StartResponseMock()

        # Simulate a web request (normally done though a WSGI server)
        response = api(helpers.create_environ(), mock)

        # Verify that the response is iterable
        self.assertTrue(_is_iterable(response))

        # Make sure start_response was passed a valid status string
        self.assertIs(mock.call_count(), 1)
        self.assertTrue(isinstance(mock.status, basestring))
        self.assertThat(mock.status, MatchesRegex('^\d+[a-zA-Z\s]+$'))

        # Verify headers is a list of tuples, each containing a pair of strings
        self.assertTrue(isinstance(mock.headers, list))
        if len(mock.headers) != 0:
            header = mock.headers[0]
            self.assertTrue(isinstance(header, tuple))
            self.assertThat(len(header), Equals(2))
            self.assertTrue(isinstance(header[0], basestring))
            self.assertTrue(isinstance(header[1], basestring))
