# -*- coding: utf-8

import datetime
import json
import xml.etree.ElementTree as et

import ddt
from testtools.matchers import raises, Not
import yaml

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
            href_text='Drill baby drill!',
            code=8733224)

    def on_patch(self, req, resp):
        raise falcon.HTTPError(falcon.HTTP_400)


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
                                      scheme='Token; UUID')


class UnauthorizedResourceSchemaless:

    def on_get(self, req, resp):
        raise falcon.HTTPUnauthorized('Authentication Required',
                                      'Missing or invalid token header.')


class NotFoundResource:

    def on_get(self, req, resp):
        raise falcon.HTTPNotFound()


class NotFoundResourceWithBody:

    def on_get(self, req, resp):
        raise falcon.HTTPNotFound(description='Not Found')


class MethodNotAllowedResource:

    def on_get(self, req, resp):
        raise falcon.HTTPMethodNotAllowed(['PUT'])


class MethodNotAllowedResourceWithHeaders:

    def on_get(self, req, resp):
        raise falcon.HTTPMethodNotAllowed(['PUT'],
                                          headers={
                                              'x-ping': 'pong'})


class MethodNotAllowedResourceWithHeadersWithAccept:

    def on_get(self, req, resp):
        raise falcon.HTTPMethodNotAllowed(['PUT'],
                                          headers={
                                              'x-ping': 'pong',
                                              'accept': 'GET,PUT'})


class MethodNotAllowedResourceWithBody:

    def on_get(self, req, resp):
        raise falcon.HTTPMethodNotAllowed(['PUT'],
                                          description='Not Allowed')


class LengthRequiredResource:

    def on_get(self, req, resp):
        raise falcon.HTTPLengthRequired('title', 'description')


class RequestEntityTooLongResource:

    def on_get(self, req, resp):
        raise falcon.HTTPRequestEntityTooLarge('Request Rejected',
                                               'Request Body Too Large')


class TemporaryRequestEntityTooLongResource:

    def __init__(self, retry_after):
        self.retry_after = retry_after

    def on_get(self, req, resp):
        raise falcon.HTTPRequestEntityTooLarge('Request Rejected',
                                               'Request Body Too Large',
                                               retry_after=self.retry_after)


class RangeNotSatisfiableResource:

    def on_get(self, req, resp):
        raise falcon.HTTPRangeNotSatisfiable(123456)


class ServiceUnavailableResource:

    def __init__(self, retry_after):
        self.retry_after = retry_after

    def on_get(self, req, resp):
        raise falcon.HTTPServiceUnavailable('Oops',
                                            'Stand by...',
                                            retry_after=self.retry_after)


class InvalidHeaderResource:

    def on_get(self, req, resp):
        raise falcon.HTTPInvalidHeader(
            'Please provide a valid token.', 'X-Auth-Token',
            code='A1001')


class MissingHeaderResource:

    def on_get(self, req, resp):
        raise falcon.HTTPMissingHeader('X-Auth-Token')


class InvalidParamResource:

    def on_get(self, req, resp):
        raise falcon.HTTPInvalidParam(
            'The value must be a hex-encoded UUID.', 'id',
            code='P1002')


class MissingParamResource:

    def on_get(self, req, resp):
        raise falcon.HTTPMissingParam('id', code='P1003')


@ddt.ddt
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
                                    'your service provider.'),
            'X-Error-Status': falcon.HTTP_503
        }

        expected_body = {
            'title': 'Storage service down',
            'description': ('The configured storage service is not '
                            'responding to requests. Please contact '
                            'your service provider.'),
            'code': 10042,
        }

        # Try it with Accept: */*
        headers['Accept'] = '*/*'
        body = self.simulate_request('/fail', headers=headers, decode='utf-8')

        self.assertEqual(self.srmock.status, headers['X-Error-Status'])
        self.assertThat(lambda: json.loads(body), Not(raises(ValueError)))
        self.assertEqual(expected_body, json.loads(body))

        # Now try it with application/json
        headers['Accept'] = 'application/json'
        body = self.simulate_request('/fail', headers=headers, decode='utf-8')

        self.assertEqual(self.srmock.status, headers['X-Error-Status'])
        self.assertThat(lambda: json.loads(body), Not(raises(ValueError)))
        self.assertEqual(json.loads(body), expected_body)

    def test_no_description_json(self):
        body = self.simulate_request('/fail', method='PATCH')
        self.assertEqual(self.srmock.status, falcon.HTTP_400)
        self.assertEqual(body, [b'{}'])

    def test_no_description_xml(self):
        body = self.simulate_request('/fail', method='PATCH',
                                     headers={'Accept': 'application/xml'})
        self.assertEqual(self.srmock.status, falcon.HTTP_400)

        expected_xml = (b'<?xml version="1.0" encoding="UTF-8"?>'
                        b'<error />')

        self.assertEqual(body, [expected_xml])

    def test_client_does_not_accept_json_or_xml(self):
        headers = {
            'Accept': 'application/x-yaml',
            'X-Error-Title': 'Storage service down',
            'X-Error-Description': ('The configured storage service is not '
                                    'responding to requests. Please contact '
                                    'your service provider'),
            'X-Error-Status': falcon.HTTP_503
        }

        body = self.simulate_request('/fail', headers=headers)
        self.assertEqual(self.srmock.status, headers['X-Error-Status'])
        self.assertEqual(body, [])

    def test_custom_error_serializer(self):
        headers = {
            'X-Error-Title': 'Storage service down',
            'X-Error-Description': ('The configured storage service is not '
                                    'responding to requests. Please contact '
                                    'your service provider'),
            'X-Error-Status': falcon.HTTP_503
        }

        expected_doc = {
            'code': 10042,
            'description': ('The configured storage service is not '
                            'responding to requests. Please contact '
                            'your service provider'),
            'title': 'Storage service down'
        }

        def _my_serializer(req, exception):
            representation = None

            preferred = req.client_prefers(('application/x-yaml',
                                            'application/json'))

            if preferred is not None:
                if preferred == 'application/json':
                    representation = exception.to_json()
                else:
                    representation = yaml.dump(exception.to_dict(),
                                               encoding=None)

            return (preferred, representation)

        def _check(media_type, deserializer):
            headers['Accept'] = media_type
            self.api.set_error_serializer(_my_serializer)
            body = self.simulate_request('/fail', headers=headers)
            self.assertEqual(self.srmock.status, headers['X-Error-Status'])

            actual_doc = deserializer(body[0].decode('utf-8'))
            self.assertEqual(expected_doc, actual_doc)

        # _check('application/x-yaml', yaml.load)
        _check('application/json', json.loads)

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

    @ddt.data(
        'application/json',
        'application/vnd.company.system.project.resource+json;v=1.1',
        'application/json-patch+json',
    )
    def test_forbidden(self, media_type):
        headers = {'Accept': media_type}

        expected_body = {
            'title': 'Request denied',
            'description': ('You do not have write permissions for this '
                            'queue.'),
            'link': {
                'text': 'Documentation related to this error',
                'href': 'http://example.com/api/rbac',
                'rel': 'help',
            },
        }

        body = self.simulate_request('/fail', headers=headers, method='POST',
                                     decode='utf-8')

        self.assertEqual(self.srmock.status, falcon.HTTP_403)
        self.assertThat(lambda: json.loads(body), Not(raises(ValueError)))
        self.assertEqual(json.loads(body), expected_body)

    def test_epic_fail_json(self):
        headers = {'Accept': 'application/json'}

        expected_body = {
            'title': 'Internet crashed',
            'description': 'Catastrophic weather event due to climate change.',
            'code': 8733224,
            'link': {
                'text': 'Drill baby drill!',
                'href': 'http://example.com/api/climate',
                'rel': 'help',
            },
        }

        body = self.simulate_request('/fail', headers=headers, method='PUT',
                                     decode='utf-8')

        self.assertEqual(self.srmock.status, falcon.HTTP_792)
        self.assertThat(lambda: json.loads(body), Not(raises(ValueError)))
        self.assertEqual(json.loads(body), expected_body)

    @ddt.data(
        'text/xml',
        'application/xml',
        'application/vnd.company.system.project.resource+xml;v=1.1',
        'application/atom+xml',
    )
    def test_epic_fail_xml(self, media_type):
        headers = {'Accept': media_type}

        expected_body = ('<?xml version="1.0" encoding="UTF-8"?>' +
                         '<error>' +
                         '<title>Internet crashed</title>' +
                         '<description>' +
                         'Catastrophic weather event due to climate change.' +
                         '</description>' +
                         '<code>8733224</code>' +
                         '<link>' +
                         '<text>Drill baby drill!</text>' +
                         '<href>http://example.com/api/climate</href>' +
                         '<rel>help</rel>' +
                         '</link>' +
                         '</error>')

        body = self.simulate_request('/fail', headers=headers, method='PUT',
                                     decode='utf-8')

        self.assertEqual(self.srmock.status, falcon.HTTP_792)
        self.assertThat(lambda: et.fromstring(body), Not(raises(ValueError)))
        self.assertEqual(body, expected_body)

    def test_unicode_json(self):
        unicode_resource = UnicodeFaultyResource()

        expected_body = {
            'title': u'Internet \xe7rashed!',
            'description': u'\xc7atastrophic weather event',
            'link': {
                'text': u'Drill b\xe1by drill!',
                'href': 'http://example.com/api/%C3%A7limate',
                'rel': 'help',
            },
        }

        self.api.add_route('/unicode', unicode_resource)
        body = self.simulate_request('/unicode', decode='utf-8')

        self.assertTrue(unicode_resource.called)
        self.assertEqual(self.srmock.status, falcon.HTTP_792)
        self.assertEqual(expected_body, json.loads(body))

    def test_unicode_xml(self):
        unicode_resource = UnicodeFaultyResource()

        expected_body = (u'<?xml version="1.0" encoding="UTF-8"?>' +
                         u'<error>' +
                         u'<title>Internet çrashed!</title>' +
                         u'<description>' +
                         u'Çatastrophic weather event' +
                         u'</description>' +
                         u'<link>' +
                         u'<text>Drill báby drill!</text>' +
                         u'<href>http://example.com/api/%C3%A7limate</href>' +
                         u'<rel>help</rel>' +
                         u'</link>' +
                         u'</error>')

        self.api.add_route('/unicode', unicode_resource)
        body = self.simulate_request('/unicode', decode='utf-8',
                                     headers={'accept': 'application/xml'})

        self.assertTrue(unicode_resource.called)
        self.assertEqual(self.srmock.status, falcon.HTTP_792)
        self.assertEqual(expected_body, body)

    def test_401(self):
        self.api.add_route('/401', UnauthorizedResource())
        self.simulate_request('/401')

        self.assertEqual(self.srmock.status, falcon.HTTP_401)
        self.assertIn(('www-authenticate', 'Token; UUID'),
                      self.srmock.headers)

    def test_401_schemaless(self):
        self.api.add_route('/401', UnauthorizedResourceSchemaless())
        self.simulate_request('/401')

        self.assertEqual(self.srmock.status, falcon.HTTP_401)
        self.assertNotIn(('www-authenticate', 'Token'), self.srmock.headers)

    def test_404_without_body(self):
        self.api.add_route('/404', NotFoundResource())
        body = self.simulate_request('/404')

        self.assertEqual(self.srmock.status, falcon.HTTP_404)
        self.assertEqual(body, [])

    def test_404_with_body(self):
        self.api.add_route('/404', NotFoundResourceWithBody())

        response = self.simulate_request('/404', decode='utf-8')
        self.assertEqual(self.srmock.status, falcon.HTTP_404)
        self.assertNotEqual(response, [])
        expected_body = {
            u'description': u'Not Found'
        }
        self.assertEqual(json.loads(response), expected_body)

    def test_405_without_body(self):
        self.api.add_route('/405', MethodNotAllowedResource())

        response = self.simulate_request('/405')
        self.assertEqual(self.srmock.status, falcon.HTTP_405)
        self.assertEqual(response, [])
        self.assertIn(('allow', 'PUT'), self.srmock.headers)

    def test_405_without_body_with_extra_headers(self):
        self.api.add_route('/405', MethodNotAllowedResourceWithHeaders())

        response = self.simulate_request('/405')
        self.assertEqual(self.srmock.status, falcon.HTTP_405)
        self.assertEqual(response, [])
        self.assertIn(('allow', 'PUT'), self.srmock.headers)
        self.assertIn(('x-ping', 'pong'), self.srmock.headers)

    def test_405_without_body_with_extra_headers_double_check(self):
        self.api.add_route('/405',
                           MethodNotAllowedResourceWithHeadersWithAccept())

        response = self.simulate_request('/405')
        self.assertEqual(self.srmock.status, falcon.HTTP_405)
        self.assertEqual(response, [])
        self.assertIn(('allow', 'PUT'), self.srmock.headers)
        self.assertNotIn(('allow', 'GET,PUT'), self.srmock.headers)
        self.assertNotIn(('allow', 'GET'), self.srmock.headers)
        self.assertIn(('x-ping', 'pong'), self.srmock.headers)

    def test_405_with_body(self):
        self.api.add_route('/405', MethodNotAllowedResourceWithBody())

        response = self.simulate_request('/405', decode='utf-8')
        self.assertEqual(self.srmock.status, falcon.HTTP_405)
        self.assertNotEqual(response, [])
        expected_body = {
            u'description': u'Not Allowed'
        }
        self.assertEqual(json.loads(response), expected_body)
        self.assertIn(('allow', 'PUT'), self.srmock.headers)

    def test_411(self):
        self.api.add_route('/411', LengthRequiredResource())
        body = self.simulate_request('/411')
        parsed_body = json.loads(body[0].decode())

        self.assertEqual(self.srmock.status, falcon.HTTP_411)
        self.assertEqual(parsed_body['title'], 'title')
        self.assertEqual(parsed_body['description'], 'description')

    def test_413(self):
        self.api.add_route('/413', RequestEntityTooLongResource())
        body = self.simulate_request('/413')
        parsed_body = json.loads(body[0].decode())

        self.assertEqual(self.srmock.status, falcon.HTTP_413)
        self.assertEqual(parsed_body['title'], 'Request Rejected')
        self.assertEqual(parsed_body['description'], 'Request Body Too Large')
        self.assertNotIn('retry-after', self.srmock.headers)

    def test_temporary_413_integer_retry_after(self):
        self.api.add_route('/413', TemporaryRequestEntityTooLongResource('6'))
        body = self.simulate_request('/413')
        parsed_body = json.loads(body[0].decode())

        self.assertEqual(self.srmock.status, falcon.HTTP_413)
        self.assertEqual(parsed_body['title'], 'Request Rejected')
        self.assertEqual(parsed_body['description'], 'Request Body Too Large')
        self.assertIn(('retry-after', '6'), self.srmock.headers)

    def test_temporary_413_datetime_retry_after(self):
        date = datetime.datetime.now() + datetime.timedelta(minutes=5)
        self.api.add_route('/413',
                           TemporaryRequestEntityTooLongResource(date))
        body = self.simulate_request('/413')
        parsed_body = json.loads(body[0].decode())

        self.assertEqual(self.srmock.status, falcon.HTTP_413)
        self.assertEqual(parsed_body['title'], 'Request Rejected')
        self.assertEqual(parsed_body['description'], 'Request Body Too Large')
        self.assertIn(('retry-after', falcon.util.dt_to_http(date)),
                      self.srmock.headers)

    def test_416(self):
        self.api = falcon.API()
        self.api.add_route('/416', RangeNotSatisfiableResource())
        body = self.simulate_request('/416', headers={'accept': 'text/xml'})

        self.assertEqual(self.srmock.status, falcon.HTTP_416)
        self.assertEqual(body, [])
        self.assertIn(('content-range', 'bytes */123456'), self.srmock.headers)
        self.assertIn(('content-length', '0'), self.srmock.headers)

    def test_503_integer_retry_after(self):
        self.api.add_route('/503', ServiceUnavailableResource(60))
        body = self.simulate_request('/503', decode='utf-8')

        expected_body = {
            u'title': u'Oops',
            u'description': u'Stand by...',
        }

        self.assertEqual(self.srmock.status, falcon.HTTP_503)
        self.assertEqual(json.loads(body), expected_body)
        self.assertIn(('retry-after', '60'), self.srmock.headers)

    def test_503_datetime_retry_after(self):
        date = datetime.datetime.now() + datetime.timedelta(minutes=5)
        self.api.add_route('/503',
                           ServiceUnavailableResource(date))
        body = self.simulate_request('/503', decode='utf-8')

        expected_body = {
            u'title': u'Oops',
            u'description': u'Stand by...',
        }

        self.assertEqual(self.srmock.status, falcon.HTTP_503)
        self.assertEqual(json.loads(body), expected_body)
        self.assertIn(('retry-after', falcon.util.dt_to_http(date)),
                      self.srmock.headers)

    def test_invalid_header(self):
        self.api.add_route('/400', InvalidHeaderResource())
        body = self.simulate_request('/400', decode='utf-8')

        expected_desc = (u'The value provided for the X-Auth-Token '
                         u'header is invalid. Please provide a valid token.')

        expected_body = {
            u'title': u'Invalid header value',
            u'description': expected_desc,
            u'code': u'A1001',
        }

        self.assertEqual(self.srmock.status, falcon.HTTP_400)
        self.assertEqual(json.loads(body), expected_body)

    def test_missing_header(self):
        self.api.add_route('/400', MissingHeaderResource())
        body = self.simulate_request('/400', decode='utf-8')

        expected_body = {
            u'title': u'Missing header value',
            u'description': u'The X-Auth-Token header is required.',
        }

        self.assertEqual(self.srmock.status, falcon.HTTP_400)
        self.assertEqual(json.loads(body), expected_body)

    def test_invalid_param(self):
        self.api.add_route('/400', InvalidParamResource())
        body = self.simulate_request('/400', decode='utf-8')

        expected_desc = (u'The "id" query parameter is invalid. The '
                         u'value must be a hex-encoded UUID.')
        expected_body = {
            u'title': u'Invalid query parameter',
            u'description': expected_desc,
            u'code': u'P1002',
        }

        self.assertEqual(self.srmock.status, falcon.HTTP_400)
        self.assertEqual(json.loads(body), expected_body)

    def test_missing_param(self):
        self.api.add_route('/400', MissingParamResource())
        body = self.simulate_request('/400', decode='utf-8')

        expected_body = {
            u'title': u'Missing query parameter',
            u'description': u'The "id" query parameter is required.',
            u'code': u'P1003',
        }

        self.assertEqual(self.srmock.status, falcon.HTTP_400)
        self.assertEqual(json.loads(body), expected_body)

    def test_misc(self):
        self._misc_test(falcon.HTTPBadRequest, falcon.HTTP_400)
        self._misc_test(falcon.HTTPNotAcceptable, falcon.HTTP_406,
                        needs_title=False)
        self._misc_test(falcon.HTTPConflict, falcon.HTTP_409)
        self._misc_test(falcon.HTTPPreconditionFailed, falcon.HTTP_412)
        self._misc_test(falcon.HTTPUnsupportedMediaType, falcon.HTTP_415,
                        needs_title=False)
        self._misc_test(falcon.HTTPInternalServerError, falcon.HTTP_500)
        self._misc_test(falcon.HTTPBadGateway, falcon.HTTP_502)
