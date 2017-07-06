import six

from falcon import API
from falcon.cmd import print_routes
from falcon.testing import redirected


class DummyResource(object):

    def on_get(self, req, resp):
        resp.body = 'Test\n'
        resp.status = '200 OK'


_api = API()
_api.add_route('/test', DummyResource())


def test_traverse_with_verbose():
    """Ensure traverse finds the proper routes and adds verbose output
    for a method function as well as the OPTIONS partial."""
    output = six.moves.StringIO()
    with redirected(stdout=output):
        print_routes.traverse(_api._router._roots, verbose=True)

    route, method, options = output.getvalue().strip().split('\n')
    assert '-> /test' == route
    # Check in both methods and options for the GET method
    # because method map is not ordered
    assert 'GET' in method + options
    if 'GET' in method:
        assert 'OPTIONS' in options
        assert 'falcon/responders.py:' in options
    else:
        assert 'OPTIONS' in method
        assert 'falcon/responders.py:' in method


def test_traverse():
    """Ensure traverse finds the proper routes."""
    output = six.moves.StringIO()
    with redirected(stdout=output):
        print_routes.traverse(_api._router._roots, verbose=False)

    route = output.getvalue().strip()
    assert '-> /test' == route
