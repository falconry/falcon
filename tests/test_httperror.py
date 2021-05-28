# -*- coding: utf-8

import datetime
import json
import wsgiref.validate
import xml.etree.ElementTree as et  # noqa: I202

import pytest
import yaml

import falcon
from falcon.http_error import NoRepresentation, OptionalRepresentation
import falcon.testing as testing
from falcon.util.deprecation import DeprecatedWarning

from _util import create_app  # NOQA


@pytest.fixture
def client(asgi):
    app = create_app(asgi)

    resource = FaultyResource()
    app.add_route('/fail', resource)

    return testing.TestClient(app)


class FaultyResource:
    def on_get(self, req, resp):
        status = req.get_header('X-Error-Status')
        title = req.get_header('X-Error-Title')
        description = req.get_header('X-Error-Description')
        code = 10042

        raise falcon.HTTPError(status, title=title, description=description, code=code)

    def on_post(self, req, resp):
        raise falcon.HTTPForbidden(
            title='Request denied',
            description='You do not have write permissions for this queue.',
            href='http://example.com/api/rbac',
        )

    def on_put(self, req, resp):
        raise falcon.HTTPError(
            falcon.HTTP_792,
            title='Internet crashed',
            description='Catastrophic weather event due to climate change.',
            href='http://example.com/api/climate',
            href_text='Drill baby drill!',
            code=8733224,
        )

    def on_patch(self, req, resp):
        raise falcon.HTTPError(falcon.HTTP_400)


class UnicodeFaultyResource:
    def __init__(self):
        self.called = False

    def on_get(self, req, resp):
        self.called = True
        raise falcon.HTTPError(
            falcon.HTTP_792,
            title='Internet \xe7rashed!',
            description='\xc7atastrophic weather event',
            href='http://example.com/api/\xe7limate',
            href_text='Drill b\xe1by drill!',
        )


class MiscErrorsResource:
    def __init__(self, exception, needs_title):
        self.needs_title = needs_title
        self._exception = exception

    def on_get(self, req, resp):
        if self.needs_title:
            raise self._exception(
                title='Excuse Us', description='Something went boink!'
            )
        else:
            raise self._exception(title='Something went boink!')


class UnauthorizedResource:
    def on_get(self, req, resp):
        raise falcon.HTTPUnauthorized(
            title='Authentication Required',
            description='Missing or invalid authorization.',
            challenges=['Basic realm="simple"'],
        )

    def on_post(self, req, resp):
        raise falcon.HTTPUnauthorized(
            title='Authentication Required',
            description='Missing or invalid authorization.',
            challenges=['Newauth realm="apps"', 'Basic realm="simple"'],
        )

    def on_put(self, req, resp):
        raise falcon.HTTPUnauthorized(
            title='Authentication Required',
            description='Missing or invalid authorization.',
            challenges=[],
        )


class NotFoundResource:
    def on_get(self, req, resp):
        raise falcon.HTTPNotFound()


class NotFoundResourceWithBody:
    def on_get(self, req, resp):
        raise falcon.HTTPNotFound(description='Not Found')


class GoneResource:
    def on_get(self, req, resp):
        raise falcon.HTTPGone()


class GoneResourceWithBody:
    def on_get(self, req, resp):
        raise falcon.HTTPGone(description='Gone with the wind')


class MethodNotAllowedResource:
    def on_get(self, req, resp):
        raise falcon.HTTPMethodNotAllowed(['PUT'])


class MethodNotAllowedResourceWithHeaders:
    def on_get(self, req, resp):
        raise falcon.HTTPMethodNotAllowed(['PUT'], headers={'x-ping': 'pong'})


class MethodNotAllowedResourceWithHeadersWithAccept:
    def on_get(self, req, resp):
        raise falcon.HTTPMethodNotAllowed(
            ['PUT'], headers={'x-ping': 'pong', 'accept': 'GET,PUT'}
        )


class MethodNotAllowedResourceWithBody:
    def on_get(self, req, resp):
        raise falcon.HTTPMethodNotAllowed(['PUT'], description='Not Allowed')


class LengthRequiredResource:
    def on_get(self, req, resp):
        raise falcon.HTTPLengthRequired(title='title', description='description')


class RequestEntityTooLongResource:
    def on_get(self, req, resp):
        raise falcon.HTTPPayloadTooLarge(
            title='Request Rejected', description='Request Body Too Large'
        )


class TemporaryRequestEntityTooLongResource:
    def __init__(self, retry_after):
        self.retry_after = retry_after

    def on_get(self, req, resp):
        raise falcon.HTTPPayloadTooLarge(
            title='Request Rejected',
            description='Request Body Too Large',
            retry_after=self.retry_after,
        )


class UriTooLongResource:
    def __init__(self, title=None, description=None, code=None):
        self.title = title
        self.description = description
        self.code = code

    def on_get(self, req, resp):
        raise falcon.HTTPUriTooLong(
            title=self.title, description=self.description, code=self.code
        )


class RangeNotSatisfiableResource:
    def on_get(self, req, resp):
        raise falcon.HTTPRangeNotSatisfiable(123456)


class TooManyRequestsResource:
    def __init__(self, retry_after=None):
        self.retry_after = retry_after

    def on_get(self, req, resp):
        raise falcon.HTTPTooManyRequests(
            title='Too many requests',
            description='1 per minute',
            retry_after=self.retry_after,
        )


class ServiceUnavailableResource:
    def __init__(self, retry_after):
        self.retry_after = retry_after

    def on_get(self, req, resp):
        raise falcon.HTTPServiceUnavailable(
            title='Oops', description='Stand by...', retry_after=self.retry_after
        )


class InvalidHeaderResource:
    def on_get(self, req, resp):
        raise falcon.HTTPInvalidHeader(
            'Please provide a valid token.', 'X-Auth-Token', code='A1001'
        )


class MissingHeaderResource:
    def on_get(self, req, resp):
        raise falcon.HTTPMissingHeader('X-Auth-Token')


class InvalidParamResource:
    def on_get(self, req, resp):
        raise falcon.HTTPInvalidParam(
            'The value must be a hex-encoded UUID.', 'id', code='P1002'
        )


class MissingParamResource:
    def on_get(self, req, resp):
        raise falcon.HTTPMissingParam('id', code='P1003')


class TestHTTPError:
    def _misc_test(self, client, exception, status, needs_title=True):
        client.app.add_route('/misc', MiscErrorsResource(exception, needs_title))

        response = client.simulate_request(path='/misc')
        assert response.status == status

    def test_base_class(self, client):
        headers = {
            'X-Error-Title': 'Storage service down',
            'X-Error-Description': (
                'The configured storage service is not '
                'responding to requests. Please contact '
                'your service provider.'
            ),
            'X-Error-Status': falcon.HTTP_503,
        }

        expected_body = {
            'title': 'Storage service down',
            'description': (
                'The configured storage service is not '
                'responding to requests. Please contact '
                'your service provider.'
            ),
            'code': 10042,
        }

        # Try it with Accept: */*
        headers['Accept'] = '*/*'
        response = client.simulate_request(path='/fail', headers=headers)

        assert response.status == headers['X-Error-Status']
        assert response.headers['vary'] == 'Accept'
        assert expected_body == response.json

        # Now try it with application/json
        headers['Accept'] = 'application/json'
        response = client.simulate_request(path='/fail', headers=headers)

        assert response.status == headers['X-Error-Status']
        assert response.json == expected_body

    def test_has_representation(self):
        with pytest.warns(DeprecatedWarning, match='has_representation is deprecated'):
            assert falcon.HTTPError(falcon.HTTP_701).has_representation is True

    def test_no_description_json(self, client):
        response = client.simulate_patch('/fail')
        assert response.status == falcon.HTTP_400
        assert response.json == {'title': '400 Bad Request'}
        assert response.headers['Content-Type'] == 'application/json'

    def test_no_description_xml(self, client):
        response = client.simulate_patch(
            path='/fail', headers={'Accept': 'application/xml'}
        )
        assert response.status == falcon.HTTP_400

        expected_xml = (
            b'<?xml version="1.0" encoding="UTF-8"?><error>'
            b'<title>400 Bad Request</title></error>'
        )

        assert response.content == expected_xml
        assert response.headers['Content-Type'] == 'application/xml'

    def test_client_does_not_accept_json_or_xml(self, client):
        headers = {
            'Accept': 'application/x-yaml',
            'X-Error-Title': 'Storage service down',
            'X-Error-Description': (
                'The configured storage service is not '
                'responding to requests. Please contact '
                'your service provider'
            ),
            'X-Error-Status': falcon.HTTP_503,
        }

        response = client.simulate_request(path='/fail', headers=headers)
        assert response.status == headers['X-Error-Status']
        assert response.headers['Vary'] == 'Accept'
        assert not response.content

    def test_custom_error_serializer(self, client):
        headers = {
            'X-Error-Title': 'Storage service down',
            'X-Error-Description': (
                'The configured storage service is not '
                'responding to requests. Please contact '
                'your service provider'
            ),
            'X-Error-Status': falcon.HTTP_503,
        }

        expected_doc = {
            'code': 10042,
            'description': (
                'The configured storage service is not '
                'responding to requests. Please contact '
                'your service provider'
            ),
            'title': 'Storage service down',
        }

        def _my_serializer(req, resp, exception):
            preferred = req.client_prefers((falcon.MEDIA_YAML, falcon.MEDIA_JSON))

            if preferred is not None:
                if preferred == falcon.MEDIA_JSON:
                    resp.data = exception.to_json()
                else:
                    resp.text = yaml.dump(exception.to_dict(), encoding=None)

                resp.content_type = preferred

        def _check(media_type, deserializer):
            headers['Accept'] = media_type
            client.app.set_error_serializer(_my_serializer)
            response = client.simulate_request(path='/fail', headers=headers)
            assert response.status == headers['X-Error-Status']

            actual_doc = deserializer(response.content.decode('utf-8'))
            assert expected_doc == actual_doc

        _check(falcon.MEDIA_YAML, yaml.safe_load)
        _check(falcon.MEDIA_JSON, json.loads)

    @pytest.mark.parametrize(
        'method,path,status',
        [
            ('GET', '/404', 404),
            ('GET', '/notfound', 404),
            ('REPORT', '/404', 405),
            ('BREW', '/notfound', 400),
        ],
    )
    def test_custom_error_serializer_optional_representation(
        self, client, method, path, status
    ):
        def _simple_serializer(req, resp, exception):
            representation = exception.to_dict()
            representation.update(status=int(exception.status[:3]))

            resp.content_type = falcon.MEDIA_JSON
            resp.media = representation

        client.app.add_route('/404', NotFoundResource())
        client.app.add_route('/notfound', NotFoundResourceWithBody())
        client.app.set_error_serializer(_simple_serializer)

        def s():
            return client.simulate_request(path=path, method=method)

        if method not in falcon.COMBINED_METHODS:
            if not client.app._ASGI:
                with pytest.warns(wsgiref.validate.WSGIWarning):
                    resp = s()
            else:
                resp = s()
        else:
            resp = s()

        assert resp.json['title']
        assert resp.json['status'] == status

    def test_custom_serializer_no_representation(self, client):
        def _chatty_serializer(req, resp, exception):
            resp.content_type = falcon.MEDIA_TEXT
            resp.text = b'You might think this error should not have a body'

        client.app.add_route('/416', RangeNotSatisfiableResource())
        client.app.set_error_serializer(_chatty_serializer)
        resp = client.simulate_get(path='/416')
        assert resp.text == 'You might think this error should not have a body'

    def test_client_does_not_accept_anything(self, client):
        headers = {
            'Accept': '45087gigo;;;;',
            'X-Error-Title': 'Storage service down',
            'X-Error-Description': (
                'The configured storage service is not '
                'responding to requests. Please contact '
                'your service provider'
            ),
            'X-Error-Status': falcon.HTTP_503,
        }

        response = client.simulate_request(path='/fail', headers=headers)
        assert response.status == headers['X-Error-Status']
        assert not response.content

    @pytest.mark.parametrize(
        'media_type',
        [
            'application/json',
            'application/vnd.company.system.project.resource+json;v=1.1',
            'application/json-patch+json',
        ],
    )
    def test_forbidden(self, client, media_type):
        headers = {'Accept': media_type}

        expected_body = {
            'title': 'Request denied',
            'description': 'You do not have write permissions for this queue.',
            'link': {
                'text': 'Documentation related to this error',
                'href': 'http://example.com/api/rbac',
                'rel': 'help',
            },
        }

        response = client.simulate_post(path='/fail', headers=headers)

        assert response.status == falcon.HTTP_403
        assert response.json == expected_body

    def test_epic_fail_json(self, client):
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

        response = client.simulate_put('/fail', headers=headers)

        assert response.status == falcon.HTTP_792
        assert response.json == expected_body

    @pytest.mark.parametrize(
        'media_type',
        [
            'text/xml',
            'application/xml',
            'application/vnd.company.system.project.resource+xml;v=1.1',
            'application/atom+xml',
        ],
    )
    def test_epic_fail_xml(self, client, media_type):
        headers = {'Accept': media_type}

        expected_body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            + '<error>'
            + '<title>Internet crashed</title>'
            + '<description>'
            + 'Catastrophic weather event due to climate change.'
            + '</description>'
            + '<code>8733224</code>'
            + '<link>'
            + '<text>Drill baby drill!</text>'
            + '<href>http://example.com/api/climate</href>'
            + '<rel>help</rel>'
            + '</link>'
            + '</error>'
        )

        response = client.simulate_put(path='/fail', headers=headers)

        assert response.status == falcon.HTTP_792
        try:
            et.fromstring(response.content.decode('utf-8'))
        except ValueError:
            pytest.fail()
        assert response.text == expected_body

    def test_unicode_json(self, client):
        unicode_resource = UnicodeFaultyResource()

        expected_body = {
            'title': 'Internet \xe7rashed!',
            'description': '\xc7atastrophic weather event',
            'link': {
                'text': 'Drill b\xe1by drill!',
                'href': 'http://example.com/api/%C3%A7limate',
                'rel': 'help',
            },
        }

        client.app.add_route('/unicode', unicode_resource)
        response = client.simulate_request(path='/unicode')

        assert unicode_resource.called
        assert response.status == falcon.HTTP_792
        assert expected_body == response.json

    def test_unicode_xml(self, client):
        unicode_resource = UnicodeFaultyResource()

        expected_body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            + '<error>'
            + '<title>Internet çrashed!</title>'
            + '<description>'
            + 'Çatastrophic weather event'
            + '</description>'
            + '<link>'
            + '<text>Drill báby drill!</text>'
            + '<href>http://example.com/api/%C3%A7limate</href>'
            + '<rel>help</rel>'
            + '</link>'
            + '</error>'
        )

        client.app.add_route('/unicode', unicode_resource)
        response = client.simulate_request(
            path='/unicode', headers={'accept': 'application/xml'}
        )

        assert unicode_resource.called
        assert response.status == falcon.HTTP_792
        assert expected_body == response.text

    def test_401(self, client):
        client.app.add_route('/401', UnauthorizedResource())
        response = client.simulate_request(path='/401')

        assert response.status == falcon.HTTP_401
        assert response.headers['www-authenticate'] == 'Basic realm="simple"'

        response = client.simulate_post('/401')

        assert response.status == falcon.HTTP_401
        assert (
            response.headers['www-authenticate']
            == 'Newauth realm="apps", Basic realm="simple"'
        )

        response = client.simulate_put('/401')

        assert response.status == falcon.HTTP_401
        assert 'www-authenticate' not in response.headers

    def test_404_without_body(self, client):
        client.app.add_route('/404', NotFoundResource())
        response = client.simulate_request(path='/404')

        assert response.status == falcon.HTTP_404
        assert response.json == falcon.HTTPNotFound().to_dict()
        assert response.json == {'title': falcon.HTTP_NOT_FOUND}

    def test_404_with_body(self, client):
        client.app.add_route('/404', NotFoundResourceWithBody())

        response = client.simulate_request(path='/404')
        assert response.status == falcon.HTTP_404
        assert response.content
        expected_body = {'title': '404 Not Found', 'description': 'Not Found'}
        assert response.json == expected_body

    def test_405_without_body(self, client):
        client.app.add_route('/405', MethodNotAllowedResource())

        response = client.simulate_request(path='/405')
        assert response.status == falcon.HTTP_405
        assert response.content == falcon.HTTPMethodNotAllowed(['PUT']).to_json()
        assert response.json == {'title': falcon.HTTP_METHOD_NOT_ALLOWED}
        assert response.headers['allow'] == 'PUT'

    def test_405_without_body_with_extra_headers(self, client):
        client.app.add_route('/405', MethodNotAllowedResourceWithHeaders())

        response = client.simulate_request(path='/405')
        assert response.status == falcon.HTTP_405
        assert response.content == falcon.HTTPMethodNotAllowed([]).to_json()
        assert response.headers['allow'] == 'PUT'
        assert response.headers['x-ping'] == 'pong'

    def test_405_without_body_with_extra_headers_double_check(self, client):
        client.app.add_route('/405', MethodNotAllowedResourceWithHeadersWithAccept())

        response = client.simulate_request(path='/405')
        assert response.status == falcon.HTTP_405
        assert response.json == falcon.HTTPMethodNotAllowed([]).to_dict()
        assert response.headers['allow'] == 'PUT'
        assert response.headers['allow'] != 'GET,PUT'
        assert response.headers['allow'] != 'GET'
        assert response.headers['x-ping'] == 'pong'

    def test_405_with_body(self, client):
        client.app.add_route('/405', MethodNotAllowedResourceWithBody())

        response = client.simulate_request(path='/405')
        assert response.status == falcon.HTTP_405
        assert response.content
        expected_body = {
            'title': '405 Method Not Allowed',
            'description': 'Not Allowed',
        }
        assert response.json == expected_body
        assert response.headers['allow'] == 'PUT'

    def test_410_without_body(self, client):
        client.app.add_route('/410', GoneResource())
        response = client.simulate_request(path='/410')

        assert response.status == falcon.HTTP_410
        assert response.content == falcon.HTTPGone().to_json()
        assert response.json == {'title': '410 Gone'}

    def test_410_with_body(self, client):
        client.app.add_route('/410', GoneResourceWithBody())

        response = client.simulate_request(path='/410')
        assert response.status == falcon.HTTP_410
        assert response.content
        expected_body = {'title': '410 Gone', 'description': 'Gone with the wind'}
        assert response.json == expected_body

    def test_411(self, client):
        client.app.add_route('/411', LengthRequiredResource())
        response = client.simulate_request(path='/411')
        assert response.status == falcon.HTTP_411

        parsed_body = response.json
        assert parsed_body['title'] == 'title'
        assert parsed_body['description'] == 'description'

    def test_413(self, client):
        client.app.add_route('/413', RequestEntityTooLongResource())
        response = client.simulate_request(path='/413')
        assert response.status == falcon.HTTP_413

        parsed_body = response.json
        assert parsed_body['title'] == 'Request Rejected'
        assert parsed_body['description'] == 'Request Body Too Large'
        assert 'retry-after' not in response.headers

    def test_temporary_413_integer_retry_after(self, client):
        client.app.add_route('/413', TemporaryRequestEntityTooLongResource('6'))
        response = client.simulate_request(path='/413')
        assert response.status == falcon.HTTP_413

        parsed_body = response.json
        assert parsed_body['title'] == 'Request Rejected'
        assert parsed_body['description'] == 'Request Body Too Large'
        assert response.headers['retry-after'] == '6'

    def test_temporary_413_datetime_retry_after(self, client):
        date = datetime.datetime.now() + datetime.timedelta(minutes=5)
        client.app.add_route('/413', TemporaryRequestEntityTooLongResource(date))
        response = client.simulate_request(path='/413')

        assert response.status == falcon.HTTP_413

        parsed_body = response.json
        assert parsed_body['title'] == 'Request Rejected'
        assert parsed_body['description'] == 'Request Body Too Large'
        assert response.headers['retry-after'] == falcon.util.dt_to_http(date)

    def test_414(self, client):
        client.app.add_route('/414', UriTooLongResource())
        response = client.simulate_request(path='/414')
        assert response.status == falcon.HTTP_414

    def test_414_with_title(self, client):
        title = 'Argh! Error!'
        client.app.add_route('/414', UriTooLongResource(title=title))
        response = client.simulate_request(path='/414', headers={})
        parsed_body = json.loads(response.content.decode())
        assert parsed_body['title'] == title

    def test_414_with_description(self, client):
        description = 'Be short please.'
        client.app.add_route('/414', UriTooLongResource(description=description))
        response = client.simulate_request(path='/414', headers={})
        parsed_body = json.loads(response.content.decode())
        assert parsed_body['description'] == description

    def test_414_with_custom_kwargs(self, client):
        code = 'someid'
        client.app.add_route('/414', UriTooLongResource(code=code))
        response = client.simulate_request(path='/414', headers={})
        parsed_body = json.loads(response.content.decode())
        assert parsed_body['code'] == code

    def test_416(self, client, asgi):
        client.app = create_app(asgi)
        client.app.add_route('/416', RangeNotSatisfiableResource())
        response = client.simulate_request(path='/416', headers={'accept': 'text/xml'})

        assert response.status == falcon.HTTP_416
        assert response.content == falcon.HTTPRangeNotSatisfiable(123456).to_xml()
        exp = (
            b'<?xml version="1.0" encoding="UTF-8"?><error>'
            b'<title>416 Range Not Satisfiable</title></error>'
        )
        assert response.content == exp
        assert response.headers['content-range'] == 'bytes */123456'
        assert response.headers['content-length'] == str(len(response.content))

    def test_429_no_retry_after(self, client):
        client.app.add_route('/429', TooManyRequestsResource())
        response = client.simulate_request(path='/429')
        parsed_body = response.json

        assert response.status == falcon.HTTP_429
        assert parsed_body['title'] == 'Too many requests'
        assert parsed_body['description'] == '1 per minute'
        assert 'retry-after' not in response.headers

    def test_429(self, client):
        client.app.add_route('/429', TooManyRequestsResource(60))
        response = client.simulate_request(path='/429')
        parsed_body = response.json

        assert response.status == falcon.HTTP_429
        assert parsed_body['title'] == 'Too many requests'
        assert parsed_body['description'] == '1 per minute'
        assert response.headers['retry-after'] == '60'

    def test_429_datetime(self, client):
        date = datetime.datetime.now() + datetime.timedelta(minutes=1)
        client.app.add_route('/429', TooManyRequestsResource(date))
        response = client.simulate_request(path='/429')
        parsed_body = response.json

        assert response.status == falcon.HTTP_429
        assert parsed_body['title'] == 'Too many requests'
        assert parsed_body['description'] == '1 per minute'
        assert response.headers['retry-after'] == falcon.util.dt_to_http(date)

    def test_503_integer_retry_after(self, client):
        client.app.add_route('/503', ServiceUnavailableResource(60))
        response = client.simulate_request(path='/503')

        expected_body = {
            'title': 'Oops',
            'description': 'Stand by...',
        }

        assert response.status == falcon.HTTP_503
        assert response.json == expected_body
        assert response.headers['retry-after'] == '60'

    def test_503_datetime_retry_after(self, client):
        date = datetime.datetime.now() + datetime.timedelta(minutes=5)
        client.app.add_route('/503', ServiceUnavailableResource(date))
        response = client.simulate_request(path='/503')

        expected_body = {
            'title': 'Oops',
            'description': 'Stand by...',
        }

        assert response.status == falcon.HTTP_503
        assert response.json == expected_body
        assert response.headers['retry-after'] == falcon.util.dt_to_http(date)

    def test_invalid_header(self, client):
        client.app.add_route('/400', InvalidHeaderResource())
        response = client.simulate_request(path='/400')

        expected_desc = (
            'The value provided for the "X-Auth-Token" '
            'header is invalid. Please provide a valid token.'
        )

        expected_body = {
            'title': 'Invalid header value',
            'description': expected_desc,
            'code': 'A1001',
        }

        assert response.status == falcon.HTTP_400
        assert response.json == expected_body

    def test_missing_header(self, client):
        client.app.add_route('/400', MissingHeaderResource())
        response = client.simulate_request(path='/400')

        expected_body = {
            'title': 'Missing header value',
            'description': 'The "X-Auth-Token" header is required.',
        }

        assert response.status == falcon.HTTP_400
        assert response.json == expected_body

    def test_invalid_param(self, client):
        client.app.add_route('/400', InvalidParamResource())
        response = client.simulate_request(path='/400')

        expected_desc = (
            'The "id" parameter is invalid. The value must be a hex-encoded UUID.'
        )
        expected_body = {
            'title': 'Invalid parameter',
            'description': expected_desc,
            'code': 'P1002',
        }

        assert response.status == falcon.HTTP_400
        assert response.json == expected_body

    def test_missing_param(self, client):
        client.app.add_route('/400', MissingParamResource())
        response = client.simulate_request(path='/400')

        expected_body = {
            'title': 'Missing parameter',
            'description': 'The "id" parameter is required.',
            'code': 'P1003',
        }

        assert response.status == falcon.HTTP_400
        assert response.json == expected_body

    def test_misc(self, client):
        self._misc_test(client, falcon.HTTPBadRequest, falcon.HTTP_400)
        self._misc_test(
            client, falcon.HTTPNotAcceptable, falcon.HTTP_406, needs_title=False
        )
        self._misc_test(client, falcon.HTTPConflict, falcon.HTTP_409)
        self._misc_test(client, falcon.HTTPPreconditionFailed, falcon.HTTP_412)
        self._misc_test(
            client, falcon.HTTPUnsupportedMediaType, falcon.HTTP_415, needs_title=False
        )
        self._misc_test(client, falcon.HTTPUnprocessableEntity, falcon.HTTP_422)
        self._misc_test(
            client,
            falcon.HTTPUnavailableForLegalReasons,
            falcon.HTTP_451,
            needs_title=False,
        )
        self._misc_test(client, falcon.HTTPInternalServerError, falcon.HTTP_500)
        self._misc_test(client, falcon.HTTPBadGateway, falcon.HTTP_502)

    def test_title_default_message_if_none(self, client):
        headers = {'X-Error-Status': falcon.HTTP_503}

        response = client.simulate_request(path='/fail', headers=headers)

        assert response.status == headers['X-Error-Status']
        assert response.json['title'] == headers['X-Error-Status']

    def test_to_json_dumps(self):
        e = falcon.HTTPError(status=falcon.HTTP_418, title='foo', description='bar')
        assert e.to_json() == b'{"title": "foo", "description": "bar"}'

        class Handler:
            def serialize(self, obj, type):
                assert type == falcon.MEDIA_JSON
                return b'{"a": "b"}'

        assert e.to_json(Handler()) == b'{"a": "b"}'

    def test_serialize_error_uses_media_handler(self, client):
        client.app.add_route('/path', NotFoundResource())
        h = client.app.resp_options.media_handlers[falcon.MEDIA_JSON]
        h._dumps = lambda x: json.dumps(x).upper()
        response = client.simulate_request(path='/path')

        assert response.status == falcon.HTTP_404
        assert response.json == {'TITLE': falcon.HTTP_NOT_FOUND.upper()}

    def test_serialize_no_json_media_handler(self, client):
        client.app.add_route('/path', NotFoundResource())
        for h in list(client.app.resp_options.media_handlers):
            if 'json' in h.casefold():
                client.app.resp_options.media_handlers.pop(h)
        response = client.simulate_request(path='/path')

        assert response.status == falcon.HTTP_404
        assert response.json == {'title': falcon.HTTP_NOT_FOUND}

    def test_MediaMalformedError(self):
        err = falcon.MediaMalformedError('foo-media')
        assert err.description == 'Could not parse foo-media body'

        err.__cause__ = ValueError('some error')
        assert err.description == 'Could not parse foo-media body - some error'


def test_kw_only():
    # only deprecated for now
    # with pytest.raises(TypeError, match='positional argument'):
    #     falcon.HTTPError(falcon.HTTP_BAD_REQUEST, 'foo', 'bar')
    with pytest.warns(DeprecatedWarning, match='positional args are deprecated'):
        falcon.HTTPError(falcon.HTTP_BAD_REQUEST, 'foo', 'bar')


def test_NoRepresentation():
    with pytest.warns(
        DeprecatedWarning,
        match='has_representation is deprecated.*The class NoRepresentation',
    ):
        assert NoRepresentation().has_representation is False


class TestOptionalRepresentation:
    def test_OptionalRepresentation_false(self):
        with pytest.warns(
            DeprecatedWarning,
            match='has_representation is deprecated.*The class OptionalRepresentation',
        ):
            or_ = OptionalRepresentation()
            or_.description = None
            assert or_.has_representation is False

    def test_OptionalRepresentation_true(self):
        with pytest.warns(
            DeprecatedWarning,
            match='has_representation is deprecated.*The class OptionalRepresentation',
        ):
            or_ = OptionalRepresentation()
            or_.description = 'foo'
            assert or_.has_representation is True
