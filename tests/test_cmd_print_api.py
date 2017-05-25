import six

from falcon import API
from falcon.cmd import print_routes
from falcon.testing import redirected


_api = API()
_api.add_route('/test', None)


def test_traverse_with_verbose():
    """Ensure traverse finds the proper routes and adds verbose output."""
    output = six.moves.StringIO()
    with redirected(stdout=output):
        print_routes.traverse(_api._router._roots, verbose=True)

    route, options = output.getvalue().strip().split('\n')
    assert '-> /test' == route
    assert 'OPTIONS' in options
    assert 'falcon/responders.py:' in options


def test_traverse():
    """Ensure traverse finds the proper routes."""
    output = six.moves.StringIO()
    with redirected(stdout=output):
        print_routes.traverse(_api._router._roots, verbose=False)

    route = output.getvalue().strip()
    assert '-> /test' == route
