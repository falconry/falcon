import json

from testtools.matchers import raises, Not

from . import helpers
import falcon


class FaultyResource:

    def on_get(self, req, resp):
        status = req.get_header('X-Error-Status')
        title = req.get_header('X-Error-Title')
        description = req.get_header('X-Error-Description')

        raise falcon.HTTPError(status, title, description)

    def on_post(self, req, resp):
        raise falcon.HTTPForbidden(
            'Request denied',
            'You do not have write permissions for this queue',
            href='http://example.com/api/rbac')

    def on_put(self, req, resp):
        raise falcon.HTTPError(
            falcon.HTTP_792,
            'Internet crashed',
            'Climate change driven catastrophic weather event',
            href='http://example.com/api/climate',
            href_rel='oops',
            href_text='Drill baby drill!')


class UnauthorizedResource:

    def on_get(self, req, resp):
        raise falcon.HTTPUnauthorized('Authentication Required',
                                      'Missing or invalid token header.',
                                      'Token')

class NotFoundResource:

    def on_get(self, req, resp):
        raise falcon.HTTPNotFound()

class MethodNotAllowedResource:

    def on_get(self, req, resp):
        raise falcon.HTTPMethodNotAllowed(['PUT'])


class InternalServerErrorResource:

    def on_get(self, req, resp):
        raise falcon.HTTPInternalServerError('Excuse Us', 'Something went'
                                             'boink!')


class TestHTTPError(helpers.TestSuite):

    def prepare(self):
        self.resource = FaultyResource()
        self.api.add_route('/fail', self.resource)

    def test_base_class(self):
        headers = {
            'X-Error-Title': 'Storage service down',
            'X-Error-Description': ('The configured storage service is not '
                                    'responding to requests. Please contact '
                                    'your service provider'),
            'X-Error-Status': falcon.HTTP_503
        }

        expected_body = [
            '{\n'
            '    "title": "Storage service down",\n'
            '    "description": "The configured storage service is not '
            'responding to requests. Please contact your service provider"\n'
            '}'
        ]

        # Try it with Accept: */*
        headers['Accept'] = '*/*'
        body = self._simulate_request('/fail', headers=headers)
        self.assertEqual(self.srmock.status, headers['X-Error-Status'])
        self.assertThat(lambda: json.loads(body[0]), Not(raises(ValueError)))
        self.assertEqual(body, expected_body)

        # Now try it with application/json
        headers['Accept'] = 'application/json'
        body = self._simulate_request('/fail', headers=headers)
        self.assertEqual(self.srmock.status, headers['X-Error-Status'])
        self.assertThat(lambda: json.loads(body[0]), Not(raises(ValueError)))
        self.assertEqual(body, expected_body)

    def test_client_does_not_accept_json(self):
        headers = {
            'Accept': 'application/soap+xml',
            'X-Error-Title': 'Storage service down',
            'X-Error-Description': ('The configured storage service is not '
                                    'responding to requests. Please contact '
                                    'your service provider'),
            'X-Error-Status': falcon.HTTP_503
        }

        body = self._simulate_request('/fail', headers=headers)
        self.assertEqual(self.srmock.status, headers['X-Error-Status'])
        self.assertEqual(body, [])

    def test_forbidden(self):
        headers = {
            'Accept': 'application/json'
        }

        expected_body = [
            '{\n'
            '    "title": "Request denied",\n'
            '    "description": "You do not have write permissions for this '
            'queue",\n'
            '    "link": {\n'
            '        "text": "API documention for this error",\n'
            '        "href": "http://example.com/api/rbac",\n'
            '        "rel": "doc"\n'
            '    }\n'
            '}'
        ]

        body = self._simulate_request('/fail', headers=headers, method='POST')
        self.assertEqual(self.srmock.status, falcon.HTTP_403)
        self.assertThat(lambda: json.loads(body[0]), Not(raises(ValueError)))
        self.assertEqual(body, expected_body)

    def test_epic_fail(self):
        headers = {
            'Accept': 'application/json'
        }

        expected_body = [
            '{\n'
            '    "title": "Internet crashed",\n'
            '    "description": "Climate change driven catastrophic weather '
            'event",\n'
            '    "link": {\n'
            '        "text": "Drill baby drill!",\n'
            '        "href": "http://example.com/api/climate",\n'
            '        "rel": "oops"\n'
            '    }\n'
            '}'
        ]

        body = self._simulate_request('/fail', headers=headers, method='PUT')
        self.assertEqual(self.srmock.status, falcon.HTTP_792)
        self.assertThat(lambda: json.loads(body[0]), Not(raises(ValueError)))
        self.assertEqual(body, expected_body)

    def test_401(self):
        self.api.add_route('/401', UnauthorizedResource())
        self._simulate_request('/401')

        self.assertEqual(self.srmock.status, falcon.HTTP_401)
        self.assertIn(('WWW-Authenticate', 'Token'), self.srmock.headers)

    def test_404(self):
        self.api.add_route('/404', NotFoundResource())
        body = self._simulate_request('/404')

        self.assertEqual(self.srmock.status, falcon.HTTP_404)
        self.assertEqual(body, [])

    def test_405(self):
        self.api.add_route('/405', MethodNotAllowedResource())
        body = self._simulate_request('/405')

        self.assertEqual(self.srmock.status, falcon.HTTP_405)
        self.assertEqual(body, [])
        self.assertIn(('Allow', 'PUT'), self.srmock.headers)

    def test_500(self):
        self.api.add_route('/500', InternalServerErrorResource())
        body = self._simulate_request('/500')

        self.assertEqual(self.srmock.status, falcon.HTTP_500)
