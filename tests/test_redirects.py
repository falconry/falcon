import pytest

import falcon
import falcon.testing as testing


@pytest.fixture
def client():
    app = falcon.API()

    resource = RedirectingResource()
    app.add_route('/', resource)

    return testing.TestClient(app)


class RedirectingResource(object):

    # NOTE(kgriffs): You wouldn't necessarily use these types of
    # http methods with these types of redirects; this is only
    # done to simplify testing.

    def on_get(self, req, resp):
        raise falcon.HTTPMovedPermanently('/moved/perm')

    def on_post(self, req, resp):
        raise falcon.HTTPFound('/found')

    def on_put(self, req, resp):
        raise falcon.HTTPSeeOther('/see/other')

    def on_delete(self, req, resp):
        raise falcon.HTTPTemporaryRedirect('/tmp/redirect')

    def on_head(self, req, resp):
        raise falcon.HTTPPermanentRedirect('/perm/redirect')


class TestRedirects(object):

    @pytest.mark.parametrize('method,expected_status,expected_location', [
        ('GET', falcon.HTTP_301, '/moved/perm'),
        ('POST', falcon.HTTP_302, '/found'),
        ('PUT', falcon.HTTP_303, '/see/other'),
        ('DELETE', falcon.HTTP_307, '/tmp/redirect'),
        ('HEAD', falcon.HTTP_308, '/perm/redirect'),
    ])
    def test_redirect(self, client, method, expected_status, expected_location):
        result = client.simulate_request(path='/', method=method)

        assert not result.content
        assert result.status == expected_status
        assert result.headers['location'] == expected_location
