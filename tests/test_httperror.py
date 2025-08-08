import datetime
import http
import json
import wsgiref.validate
import xml.etree.ElementTree as et

import pytest

import falcon
from falcon.constants import MEDIA_JSON
from falcon.constants import MEDIA_XML
from falcon.constants import MEDIA_YAML
from falcon.media import BaseHandler
import falcon.testing as testing
from falcon.util.deprecation import DeprecatedWarning

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


@pytest.fixture
def client(asgi, util):
    app = util.create_app(asgi)

    resource = FaultyResource()
    app.add_route('/fail', resource)

    return testing.TestClient(app)


@pytest.fixture(
    params=[
        pytest.param(True, id='with_xml'),
        pytest.param(False, id='without_xml'),
        pytest.param(None, id='default_xml'),
    ]
)
def enable_xml(request):
    def go(app):
        if request.param is not None:
            app.resp_options.xml_error_serialization = request.param
        return request.param is not False

    return go


class FaultyResource:
    def on_get(self, req, resp):
        status = req.get_header('X-Error-Status')
        title = req.get_header('X-Error-Title')
        description = req.get_header('X-Error-Description')
        code = 10042

        status_type = req.get_header('X-Error-Status-Type')
        if status_type:
            assert status

        if status_type == 'int':
            status = int(status)
        elif status_type == 'bytes':
            status = status.encode()
        elif status_type == 'HTTPStatus':
            status = http.HTTPStatus(int(status))
        elif status_type == 'str':
            pass
        elif status_type is not None:
            pytest.fail(f'status_type {status_type} not recognized')

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
            792,  # NOTE(kgriffs): Test that an int is acceptable even for 7xx codes
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
        raise falcon.HTTPContentTooLarge(
            title='Request Rejected', description='Request Body Too Large'
        )


class TemporaryRequestEntityTooLongResource:
    def __init__(self, retry_after):
        self.retry_after = retry_after

    def on_get(self, req, resp):
        raise falcon.HTTPContentTooLarge(
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

    def test_no_description_json(self, client):
        response = client.simulate_patch('/fail')
        assert response.status == falcon.HTTP_400
        assert response.json == {'title': '400 Bad Request'}
        assert response.content_type == 'application/json'

    def test_no_description_xml(self, client):
        client.app.resp_options.xml_error_serialization = True
        response = client.simulate_patch(
            path='/fail', headers={'Accept': 'application/xml'}
        )
        assert response.status == falcon.HTTP_400

        expected_xml = (
            b'<?xml version="1.0" encoding="UTF-8"?><error>'
            b'<title>400 Bad Request</title></error>'
        )

        assert response.content == expected_xml
        assert response.content_type == 'application/xml'

    @pytest.mark.parametrize('custom_xml', [True, False])
    def test_xml_enable(self, client, enable_xml, custom_xml):
        has_xml = enable_xml(client.app)
        client.app.resp_options.default_media_type = 'app/foo'
        accept = 'app/falcon+xml' if custom_xml else 'application/xml'
        response = client.simulate_patch(path='/fail', headers={'Accept': accept})
        assert response.status == falcon.HTTP_400

        if has_xml:
            expected_xml = (
                b'<?xml version="1.0" encoding="UTF-8"?><error>'
                b'<title>400 Bad Request</title></error>'
            )
            assert response.content == expected_xml
        else:
            assert response.content == b''
        if has_xml or custom_xml:
            assert response.content_type == 'application/xml'
        else:
            assert response.content_type == 'app/foo'

    def test_to_xml_deprecated(self):
        with pytest.warns(
            DeprecatedWarning,
            match='The internal error serialization to XML is deprecated.',
        ):
            res = falcon.HTTPGone().to_xml()
        assert res == falcon.HTTPGone()._to_xml()

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

    @pytest.mark.skipif(yaml is None, reason='PyYAML is required for this test')
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
        client.app.resp_options.xml_error_serialization = True
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
        client.app.resp_options.xml_error_serialization = True
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

    def test_416(self, client, asgi, util):
        client.app = util.create_app(asgi)
        client.app.resp_options.xml_error_serialization = True
        client.app.add_route('/416', RangeNotSatisfiableResource())
        response = client.simulate_request(path='/416', headers={'accept': 'text/xml'})

        assert response.status == falcon.HTTP_416
        assert response.content == falcon.HTTPRangeNotSatisfiable(123456)._to_xml()
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

    @pytest.mark.parametrize(
        'status, status_type',
        [
            (falcon.HTTP_503, 'str'),
            (falcon.HTTP_503, 'bytes'),
            (503, 'int'),
            (503, 'str'),
            (503, 'bytes'),
            (503, 'HTTPStatus'),
        ],
    )
    def test_title_default_message_if_none(self, status, status_type, client):
        headers = {
            'X-Error-Status': str(status),
            'X-Error-Status-Type': status_type,
        }

        response = client.simulate_request(path='/fail', headers=headers)

        assert response.json['title'] == falcon.HTTP_503
        assert response.status_code == 503

    def test_to_json_dumps(self):
        e = falcon.HTTPError(status=418, title='foo', description='bar')
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

    def test_kw_only(self):
        with pytest.raises(TypeError, match='positional argument'):
            falcon.HTTPError(falcon.HTTP_BAD_REQUEST, 'foo', 'bar')


JSON_CONTENT = b'{"title": "410 Gone"}'
JSON = (MEDIA_JSON, MEDIA_JSON, JSON_CONTENT)
CUSTOM_JSON = ('custom/any+json', MEDIA_JSON, JSON_CONTENT)

XML_CONTENT = (
    b'<?xml version="1.0" encoding="UTF-8"?><error><title>410 Gone</title></error>'
)
XML = (MEDIA_XML, MEDIA_XML, XML_CONTENT)
CUSTOM_XML = ('custom/any+xml', MEDIA_XML, XML_CONTENT)

YAML = (MEDIA_YAML, MEDIA_YAML, b'title: 410 Gone!')
ASYNC_ONLY = ('application/only_async', 'application/only_async', b'this is async')
ASYNC_WITH_SYNC = (
    'application/async_with_sync',
    'application/async_with_sync',
    b'this is sync instead',
)


class FakeYamlMediaHandler(BaseHandler):
    def serialize(self, media, content_type=None):
        assert media == {'title': '410 Gone'}
        return b'title: 410 Gone!'


class AsyncOnlyMediaHandler(BaseHandler):
    async def serialize_async(self, media, content_type=None):
        assert media == {'title': '410 Gone'}
        return b'this is async'


class SyncInterfaceMediaHandler(AsyncOnlyMediaHandler):
    def serialize(self, media, content_type=None):
        assert media == {'title': '410 Gone'}
        return b'this is sync instead'

    _serialize_sync = serialize


class TestDefaultSerializeError:
    @pytest.fixture
    def client(self, util, asgi):
        app = util.create_app(asgi)
        app.add_route('/', GoneResource())
        return testing.TestClient(app)

    def test_unknown_accept(self, client):
        res = client.simulate_get(headers={'Accept': 'foo/bar'})
        assert res.content_type == 'application/json'
        assert res.headers['vary'] == 'Accept'
        assert res.content == b''

    @pytest.mark.parametrize('has_json_handler', [True, False])
    def test_defaults_to_json(self, client, has_json_handler):
        if not has_json_handler:
            client.app.req_options.media_handlers.pop(MEDIA_JSON)
            client.app.resp_options.media_handlers.pop(MEDIA_JSON)
        res = client.simulate_get()
        assert res.content_type == 'application/json'
        assert res.headers['vary'] == 'Accept'
        assert res.content == JSON_CONTENT

    @pytest.mark.parametrize(
        'accept, content_type, content',
        (JSON, XML, CUSTOM_JSON, CUSTOM_XML, YAML, ASYNC_ONLY, ASYNC_WITH_SYNC),
    )
    def test_serializes_error_to_preferred_by_sender(
        self, accept, content_type, content, client, asgi
    ):
        client.app.resp_options.xml_error_serialization = True
        client.app.resp_options.media_handlers[MEDIA_YAML] = FakeYamlMediaHandler()
        client.app.resp_options.media_handlers[ASYNC_WITH_SYNC[0]] = (
            SyncInterfaceMediaHandler()
        )
        if asgi:
            client.app.resp_options.media_handlers[ASYNC_ONLY[0]] = (
                AsyncOnlyMediaHandler()
            )
        res = client.simulate_get(headers={'Accept': accept})
        assert res.headers['vary'] == 'Accept'
        if content_type == ASYNC_ONLY[0] and not asgi:
            # media-json is the default content type
            assert res.content_type == MEDIA_JSON
            assert res.content == b''
        else:
            assert res.content_type == content_type
            assert res.content == content

    def test_json_async_only_error(self, util):
        app = util.create_app(True)
        app.add_route('/', GoneResource())
        app.resp_options.media_handlers[MEDIA_JSON] = AsyncOnlyMediaHandler()
        client = testing.TestClient(app)
        with pytest.raises(NotImplementedError, match='requires the sync interface'):
            client.simulate_get()

    @pytest.mark.parametrize('accept', [MEDIA_XML, 'application/xhtml+xml'])
    def test_add_xml_handler(self, client, enable_xml, accept):
        enable_xml(client.app)
        client.app.resp_options.media_handlers[MEDIA_XML] = FakeYamlMediaHandler()
        res = client.simulate_get(headers={'Accept': accept})
        assert res.content_type == MEDIA_XML
        assert res.content == YAML[-1]

    @pytest.mark.parametrize(
        'accept, content_type',
        [
            (
                # firefox
                'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,'
                'image/webp,image/png,image/svg+xml,*/*;q=0.8',
                MEDIA_XML,
            ),
            (
                # safari / chrome
                'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,'
                'image/apng,*/*;q=0.8',
                MEDIA_XML,
            ),
            ('text/html, application/xhtml+xml, image/jxr, */*', MEDIA_JSON),  # edge
            (f'text/html,{MEDIA_YAML};q=0.8,*/*;q=0.7', MEDIA_YAML),
            (f'text/html,{MEDIA_YAML};q=0.8,{MEDIA_JSON};q=0.8', MEDIA_JSON),
        ],
    )
    def test_hard_content_types(self, client, accept, content_type, enable_xml):
        has_xml = enable_xml(client.app)
        client.app.resp_options.default_media_type = 'my_type'
        client.app.resp_options.media_handlers[MEDIA_YAML] = FakeYamlMediaHandler()
        res = client.simulate_get(headers={'Accept': accept})
        if has_xml or content_type != MEDIA_XML:
            assert res.content_type == content_type
        else:
            assert res.content_type == MEDIA_JSON
