import json

from testtools.matchers import raises, Not

import falcon.testing as testing
import falcon


class FaultyResource:

    def on_get(self, req, resp):
        status = req.get_header('X-Error-Status')
        title = req.get_header('X-Error-Title')
        description = req.get_header('X-Error-Description')
        code = 10042

        raise falcon.HTTPError(status, title, description, code=code)

    def on_post(self, req, resp):
        raise falcon.HTTPForbidden(
            'Request denied',
            'You do not have write permissions for this queue.',
            href='http://example.com/api/rbac')

    def on_put(self, req, resp):
        raise falcon.HTTPError(
            falcon.HTTP_792,
            'Internet crashed',
            'Catastrophic weather event due to climate change.',
            href='http://example.com/api/climate',
            href_text='Drill baby drill!')

    def on_patch(self, req, resp):
        raise falcon.HTTPError(falcon.HTTP_400, 'No-can-do')


class UnicodeFaultyResource(object):

    def __init__(self):
        self.called = False

    def on_get(self, req, resp):
        self.called = True
        raise falcon.HTTPError(
            falcon.HTTP_792,
            u'Internet \xe7rashed!',
            u'\xc7atastrophic weather event',
            href=u'http://example.com/api/\xe7limate',
            href_text=u'Drill b\xe1by drill!')


class MiscErrorsResource:

    def __init__(self, exception, needs_title):
        self.needs_title = needs_title
        self._exception = exception

    def on_get(self, req, resp):
        if self.needs_title:
            raise self._exception('Excuse Us', 'Something went boink!')
        else:
            raise self._exception('Something went boink!')


class UnauthorizedResource:

    def on_get(self, req, resp):
        raise falcon.HTTPUnauthorized('Authentication Required',
                                      'Missing or invalid token header.',
                                      'Token')


class UnauthorizedResourceSchemaless:

    def on_get(self, req, resp):
        raise falcon.HTTPUnauthorized('Authentication Required',
                                      'Missing or invalid token header.')


class NotFoundResource:

    def on_get(self, req, resp):
        raise falcon.HTTPNotFound()


class MethodNotAllowedResource:

    def on_get(self, req, resp):
        raise falcon.HTTPMethodNotAllowed(['PUT'])


class LengthRequiredResource:

    def on_get(self, req, resp):
        raise falcon.HTTPLengthRequired('title', 'description')


class RangeNotSatisfiableResource:

    def on_get(self, req, resp):
        raise falcon.HTTPRangeNotSatisfiable(123456)

    def on_put(self, req, resp):
        raise falcon.HTTPRangeNotSatisfiable(123456, 'x-falcon/peregrine')


class ServiceUnavailableResource:

    def on_get(self, req, resp):
        raise falcon.HTTPServiceUnavailable('Oops', 'Stand by...', 60)


class TestHTTPError(testing.TestBase):

    def before(self):
        self.resource = FaultyResource()
        self.api.add_route('/fail', self.resource)

    def _misc_test(self, exception, status, needs_title=True):
        self.api.add_route('/misc', MiscErrorsResource(exception, needs_title))

        self.simulate_request('/misc')
        self.assertEqual(self.srmock.status, status)

    def test_base_class(self):
        headers = {
            'X-Error-Title': 'Storage service down',
            'X-Error-Description': ('The configured storage service is not '
                                    'responding to requests. Please contact '
                                    'your service provider'),
            'X-Error-Status': falcon.HTTP_503
        }

        expected_body = [
            b'{\n'
            b'    "title": "Storage service down",\n'
            b'    "description": "The configured storage service is not '
            b'responding to requests. Please contact your service provider",\n'
            b'    "code": 10042\n'
            b'}'
        ]

        # Try it with Accept: */*
        headers['Accept'] = '*/*'
        body = self.simulate_request('/fail', headers=headers)
        self.assertEqual(self.srmock.status, headers['X-Error-Status'])
        self.assertThat(lambda: json.loads(body[0]), Not(raises(ValueError)))
        self.assertEqual(expected_body, body)

        # Now try it with application/json
        headers['Accept'] = 'application/json'
        body = self.simulate_request('/fail', headers=headers)
        self.assertEqual(self.srmock.status, headers['X-Error-Status'])
        self.assertThat(lambda: json.loads(body[0]), Not(raises(ValueError)))
        self.assertEqual(body, expected_body)

    def test_no_description(self):
        body = self.simulate_request('/fail', method='PATCH')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)
        self.assertEqual(body, [b'{\n    "title": "No-can-do"\n}'])

    def test_client_does_not_accept_json(self):
        headers = {
            'Accept': 'application/soap+xml',
            'X-Error-Title': 'Storage service down',
            'X-Error-Description': ('The configured storage service is not '
                                    'responding to requests. Please contact '
                                    'your service provider'),
            'X-Error-Status': falcon.HTTP_503
        }

        body = self.simulate_request('/fail', headers=headers)
        self.assertEqual(self.srmock.status, headers['X-Error-Status'])
        self.assertEqual(body, [])

    def test_client_does_not_accept_anything(self):
        headers = {
            'Accept': '45087gigo;;;;',
            'X-Error-Title': 'Storage service down',
            'X-Error-Description': ('The configured storage service is not '
                                    'responding to requests. Please contact '
                                    'your service provider'),
            'X-Error-Status': falcon.HTTP_503
        }

        body = self.simulate_request('/fail', headers=headers)
        self.assertEqual(self.srmock.status, headers['X-Error-Status'])
        self.assertEqual(body, [])

    def test_forbidden(self):
        headers = {
            'Accept': 'application/json'
        }

        expected_body = [
            b'{\n'
            b'    "title": "Request denied",\n'
            b'    "description": "You do not have write permissions for this '
            b'queue.",\n'
            b'    "link": {\n'
            b'        "text": "API documention for this error",\n'
            b'        "href": "http://example.com/api/rbac",\n'
            b'        "rel": "help"\n'
            b'    }\n'
            b'}'
        ]

        body = self.simulate_request('/fail', headers=headers, method='POST')
        self.assertEqual(self.srmock.status, falcon.HTTP_403)
        self.assertThat(lambda: json.loads(body[0]), Not(raises(ValueError)))
        self.assertEqual(body, expected_body)

    def test_epic_fail(self):
        headers = {
            'Accept': 'application/json'
        }

        expected_body = [
            b'{\n'
            b'    "title": "Internet crashed",\n'
            b'    "description": "Catastrophic weather event due to climate '
            b'change.",\n'
            b'    "link": {\n'
            b'        "text": "Drill baby drill!",\n'
            b'        "href": "http://example.com/api/climate",\n'
            b'        "rel": "help"\n'
            b'    }\n'
            b'}'
        ]

        body = self.simulate_request('/fail', headers=headers, method='PUT')
        self.assertEqual(self.srmock.status, falcon.HTTP_792)
        self.assertThat(lambda: json.loads(body[0]), Not(raises(ValueError)))
        self.assertEqual(body, expected_body)

    def test_unicode(self):
        unicode_resource = UnicodeFaultyResource()
        expected_body = [
            b'{\n'
            b'    "title": "Internet \xc3\xa7rashed!",\n'
            b'    "description": "\xc3\x87atastrophic weather event",\n'
            b'    "link": {\n'
            b'        "text": "Drill b\xc3\xa1by drill!",\n'
            b'        "href": "http://example.com/api/%C3%A7limate",\n'
            b'        "rel": "help"\n'
            b'    }\n'
            b'}'
        ]

        self.api.add_route('/unicode', unicode_resource)
        body = self.simulate_request('/unicode')

        self.assertTrue(unicode_resource.called)
        #self.assertEqual(self.srmock.status, falcon.HTTP_792)
        self.assertEquals(expected_body, body)

    def test_401(self):
        self.api.add_route('/401', UnauthorizedResource())
        self.simulate_request('/401')

        self.assertEqual(self.srmock.status, falcon.HTTP_401)
        self.assertIn(('WWW-Authenticate', 'Token'), self.srmock.headers)

    def test_401_schemaless(self):
        self.api.add_route('/401', UnauthorizedResourceSchemaless())
        self.simulate_request('/401')

        self.assertEqual(self.srmock.status, falcon.HTTP_401)
        self.assertNotIn(('WWW-Authenticate', 'Token'), self.srmock.headers)

    def test_404(self):
        self.api.add_route('/404', NotFoundResource())
        body = self.simulate_request('/404')

        self.assertEqual(self.srmock.status, falcon.HTTP_404)
        self.assertEqual(body, [])

    def test_405(self):
        self.api.add_route('/405', MethodNotAllowedResource())
        body = self.simulate_request('/405')

        self.assertEqual(self.srmock.status, falcon.HTTP_405)
        self.assertEqual(body, [])
        self.assertIn(('Allow', 'PUT'), self.srmock.headers)

    def test_411(self):
        self.api.add_route('/411', LengthRequiredResource())
        body = self.simulate_request('/411')
        parsed_body = json.loads(body[0].decode())

        self.assertEqual(self.srmock.status, falcon.HTTP_411)
        self.assertEqual(parsed_body['title'], 'title')
        self.assertEqual(parsed_body['description'], 'description')

    def test_416_default_media_type(self):
        self.api = falcon.API('application/xml')
        self.api.add_route('/416', RangeNotSatisfiableResource())
        body = self.simulate_request('/416')

        self.assertEqual(self.srmock.status, falcon.HTTP_416)
        self.assertEqual(body, [])
        self.assertIn(('Content-Range', 'bytes */123456'), self.srmock.headers)
        self.assertIn(('Content-Type', 'application/xml'), self.srmock.headers)
        self.assertNotIn(('Content-Length', '0'), self.srmock.headers)

    def test_416_custom_media_type(self):
        self.api.add_route('/416', RangeNotSatisfiableResource())
        body = self.simulate_request('/416', method='PUT')

        self.assertEqual(self.srmock.status, falcon.HTTP_416)
        self.assertEqual(body, [])
        self.assertIn(('Content-Range', 'bytes */123456'),
                      self.srmock.headers)
        self.assertIn(('Content-Type', 'x-falcon/peregrine'),
                      self.srmock.headers)

    def test_503(self):
        self.api.add_route('/503', ServiceUnavailableResource())
        body = self.simulate_request('/503')

        expected_body = (b'{\n    "title": "Oops",\n    "description": '
                         b'"Stand by..."\n}')

        self.assertEqual(self.srmock.status, falcon.HTTP_503)
        self.assertEqual(body, [expected_body])
        self.assertIn(('Retry-After', '60'), self.srmock.headers)

    def test_misc(self):
        self._misc_test(falcon.HTTPBadRequest, falcon.HTTP_400)
        self._misc_test(falcon.HTTPNotAcceptable, falcon.HTTP_406,
                        needs_title=False)
        self._misc_test(falcon.HTTPConflict, falcon.HTTP_409)
        self._misc_test(falcon.HTTPPreconditionFailed, falcon.HTTP_412)
        self._misc_test(falcon.HTTPUnsupportedMediaType, falcon.HTTP_415,
                        needs_title=False)
        self._misc_test(falcon.HTTPUpgradeRequired, falcon.HTTP_426)
        self._misc_test(falcon.HTTPInternalServerError, falcon.HTTP_500)
        self._misc_test(falcon.HTTPBadGateway, falcon.HTTP_502)
