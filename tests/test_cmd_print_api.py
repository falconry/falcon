import io

from falcon import App
from falcon.cmd import print_routes
from falcon.testing import redirected

try:
    import cython
except ImportError:
    cython = None


class DummyResource:

    def on_get(self, req, resp):
        resp.body = 'Test\n'
        resp.status = '200 OK'


_api = App()
_api.add_route('/test', DummyResource())


def test_traverse_with_verbose():
    """Ensure traverse() finds the proper routes and outputs verbose info."""

    output = io.StringIO()
    with redirected(stdout=output):
        print_routes.traverse(_api._router._roots, verbose=True)

    route, get_info, options_info = output.getvalue().strip().split('\n')
    assert '-> /test' == route

    # NOTE(kgriffs) We might receive these in either order, since the
    # method map is not ordered, so check and swap if necessary.
    if options_info.startswith('-->GET'):
        get_info, options_info = options_info, get_info

    assert options_info.startswith('-->OPTIONS')
    if cython:
        assert options_info.endswith('[unknown file]')
    else:
        assert 'falcon/responders.py:' in options_info

    assert get_info.startswith('-->GET')
    # NOTE(vytas): This builds upon the fact that on_get is defined on line 14
    # in this file. Adjust the test if the said responder is relocated, or just
    # check for any number if this becomes too painful to maintain.
    assert get_info.endswith('tests/test_cmd_print_api.py:15')


def test_traverse():
    """Ensure traverse() finds the proper routes."""
    output = io.StringIO()
    with redirected(stdout=output):
        print_routes.traverse(_api._router._roots, verbose=False)

    route = output.getvalue().strip()
    assert '-> /test' == route
