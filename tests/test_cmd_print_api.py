try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

from falcon import API
from falcon.cmd import print_routes
from falcon.testing import redirected


_api = API()
_api.add_route('/test', None)


class TestPrintRoutes(object):
    def test_traverse_with_verbose(self):
        """Ensure traverse finds the proper routes and adds verbose output."""
        output = StringIO()
        with redirected(stdout=output):
            print_routes.traverse(_api._router._roots, verbose=True)

        route, options = output.getvalue().strip().split('\n')
        assert '-> /test' == route
        assert 'OPTIONS' in options
        assert 'falcon/responders.py:' in options

    def test_traverse(self):
        """Ensure traverse finds the proper routes."""
        output = StringIO()
        with redirected(stdout=output):
            print_routes.traverse(_api._router._roots, verbose=False)

        route = output.getvalue().strip()
        assert '-> /test' == route
