import ddt

import falcon
import falcon.testing as testing


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


@ddt.ddt
class TestRedirects(testing.TestBase):

    def before(self):
        self.api.add_route('/', RedirectingResource())

    @ddt.data(
        ('GET', falcon.HTTP_301, '/moved/perm'),
        ('POST', falcon.HTTP_302, '/found'),
        ('PUT', falcon.HTTP_303, '/see/other'),
        ('DELETE', falcon.HTTP_307, '/tmp/redirect'),
        ('HEAD', falcon.HTTP_308, '/perm/redirect'),
    )
    @ddt.unpack
    def test_redirect(self, method, expected_status, expected_location):
        result = self.simulate_request('/', method=method)

        self.assertEqual(result, [])
        self.assertEqual(self.srmock.status, expected_status)
        self.assertEqual(self.srmock.headers_dict['location'],
                         expected_location)
