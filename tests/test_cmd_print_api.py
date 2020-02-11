import io
from os.path import normpath

import pytest

from falcon.cmd import print_routes
from falcon.testing import redirected

from _util import create_app  # NOQA


class DummyResource:

    def on_get(self, req, resp):
        resp.body = 'Test\n'
        resp.status = '200 OK'


class DummyResourceAsync:

    async def on_get(self, req, resp):
        resp.body = 'Test\n'
        resp.status = '200 OK'


@pytest.fixture
def app(asgi):
    app = create_app(asgi)
    app.add_route('/test', DummyResourceAsync() if asgi else DummyResource())

    return app


def test_traverse_with_verbose(app):
    """Ensure traverse() finds the proper routes and outputs verbose info."""

    output = io.StringIO()
    with redirected(stdout=output):
        print_routes.traverse(app._router._roots, verbose=True)

    route, get_info, options_info = output.getvalue().strip().split('\n')
    assert '-> /test' == route

    # NOTE(kgriffs) We might receive these in either order, since the
    # method map is not ordered, so check and swap if necessary.
    if options_info.startswith('-->GET'):
        get_info, options_info = options_info, get_info

    assert options_info.startswith('-->OPTIONS')
    assert '{}:'.format(normpath('falcon/responders.py')) in options_info

    assert get_info.startswith('-->GET')

    # NOTE(vytas): This builds upon the fact that on_get is defined on line
    # 18 or 25 (in the case of DummyResourceAsync) in the present file.
    # Adjust the test if the said responder is relocated, or just check for
    # any number if this becomes too painful to maintain.
    path = normpath('tests/test_cmd_print_api.py')

    assert (
        get_info.endswith('{}:14'.format(path)) or
        get_info.endswith('{}:21'.format(path))
    )


def test_traverse(app):
    """Ensure traverse() finds the proper routes."""
    output = io.StringIO()
    with redirected(stdout=output):
        print_routes.traverse(app._router._roots, verbose=False)

    route = output.getvalue().strip()
    assert '-> /test' == route
