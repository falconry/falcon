# NOTE(myusko): A file contains temporary tests for API alias
# and it will be deleted once the API alias will be removed

import pytest

import falcon
import falcon.testing as testing
from falcon.util.deprecation import DeprecatedWarning


class CookieResource:
    def on_get(self, req, resp):
        resp.set_cookie('foo', 'bar')


@pytest.fixture
def alias_client():
    with pytest.warns(DeprecatedWarning, match='API class will be removed'):
        api = falcon.API()
    api.add_route('/get-cookie', CookieResource())
    return testing.TestClient(api)


@pytest.fixture
def app_client():
    app = falcon.App()
    app.add_route('/get-cookie', CookieResource())
    return testing.TestClient(app)


def test_cookies(alias_client, app_client):
    alias_result = alias_client.simulate_get('/get-cookie')

    alias_cookie = alias_result.cookies['foo']
    assert alias_cookie.name == 'foo'
    assert alias_cookie.value == 'bar'

    app_client_result = app_client.simulate_get('/get-cookie')
    app_cookie = app_client_result.cookies['foo']
    assert app_cookie.name == 'foo'
    assert app_cookie.value == 'bar'


def test_alias_equals_to_app(alias_client):
    with pytest.warns(DeprecatedWarning, match='API class will be removed'):
        api = falcon.API()
    assert isinstance(api, falcon.API)


# Tests for the falcon.sys re-export deprecation (#2630). The alias is
# scheduled for removal in Falcon 5.0; until then it must keep working
# but warn on access.

def test_falcon_sys_emits_deprecation_warning():
    import sys as stdlib_sys

    with pytest.warns(DeprecatedWarning, match='falcon.sys is deprecated'):
        accessed = falcon.sys
    assert accessed is stdlib_sys


def test_falcon_unknown_attribute_still_raises_attribute_error():
    # The new module __getattr__ must not swallow lookups for other
    # missing attributes — those still need to raise AttributeError so
    # `hasattr(falcon, 'something_that_does_not_exist')` returns False.
    with pytest.raises(AttributeError, match='no attribute'):
        falcon.this_attribute_does_not_exist  # noqa: B018
