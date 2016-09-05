import sys
import testtools

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from falcon import API
from falcon.cmd import print_routes


_api = API()
_api.add_route('/test', None)

STDOUT = sys.stdout


class TestPrintRoutes(testtools.TestCase):

    def setUp(self):
        """Capture stdout"""
        super(TestPrintRoutes, self).setUp()
        self.output = StringIO()
        sys.stdout = self.output

    def tearDown(self):
        """Reset stdout"""
        super(TestPrintRoutes, self).tearDown()
        self.output.close()
        del self.output
        sys.stdout = STDOUT

    def test_traverse_with_verbose(self):
        """Ensure traverse finds the proper routes and adds verbose output."""
        print_routes.traverse(
            _api._router._roots,
            verbose=True)

        route, options = self.output.getvalue().strip().split('\n')
        self.assertEquals('-> /test', route)
        self.assertTrue('OPTIONS' in options)
        self.assertTrue('falcon/falcon/responders.py:' in options)

    def test_traverse(self):
        """Ensure traverse finds the proper routes."""
        print_routes.traverse(
            _api._router._roots,
            verbose=False)

        route = self.output.getvalue().strip()
        self.assertEquals('-> /test', route)
