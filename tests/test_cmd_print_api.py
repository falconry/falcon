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
    """Ensure traverse() finds the proper routes and outputs verbose info."""

    output = six.moves.StringIO()
    with redirected(stdout=output):
        print_routes.traverse(_api._router._roots, verbose=True)

    route, get_info, options_info = output.getvalue().strip().split('\n')
    assert '-> /test' == route

    # NOTE(kgriffs) We might receive these in either order, since the
    # method map is not ordered, so check and swap if necessary.
    if options_info.startswith('-->GET'):
        get_info, options_info = options_info, get_info

    assert options_info.startswith('-->OPTIONS')
    assert 'falcon/responders.py:' in options_info

    assert get_info.startswith('-->GET')
    assert 'tests/test_cmd_print_api.py:' in get_info


def test_traverse():
    """Ensure traverse() finds the proper routes."""
    output = six.moves.StringIO()
    with redirected(stdout=output):
        print_routes.traverse(_api._router._roots, verbose=False)

    route = output.getvalue().strip()
    assert '-> /test' == route
