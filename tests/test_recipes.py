import sys
import types
import unittest.mock

import pytest

import falcon
import falcon.testing


class TestMultipartMixed:
    """Test parsing example from the now-obsolete RFC 1867:

    --AaB03x
    Content-Disposition: form-data; name="field1"

    Joe Blow
    --AaB03x
    Content-Disposition: form-data; name="docs"
    Content-Type: multipart/mixed; boundary=BbC04y

    --BbC04y
    Content-Disposition: attachment; filename="file1.txt"

    This is file1.

    --BbC04y
    Content-Disposition: attachment; filename="file2.txt"

    Hello, World!

    --BbC04y--

    --AaB03x--
    """

    @classmethod
    def prepare_form(cls):
        lines = [line.strip() for line in cls.__doc__.splitlines()[2:]]

        # NOTE(vytas): On CPython 3.13-rc1, the last newline was missing.
        if lines[-1]:
            lines.append('')

        return '\r\n'.join(lines).encode()

    def test_parse(self, util):
        recipe = util.load_module('examples/recipes/multipart_mixed_main.py')

        result = falcon.testing.simulate_post(
            recipe.app,
            '/forms',
            body=self.prepare_form(),
            content_type='multipart/form-data; boundary=AaB03x',
        )
        assert result.status_code == 200
        assert result.json == {
            'file1.txt': 'This is file1.\r\n',
            'file2.txt': 'Hello, World!\r\n',
        }


class TestOutputCSV:
    @pytest.mark.parametrize(
        'recipe,expected_head',
        [
            ('output_csv_text', '"fruit","quantity"\r\n"apples",13\r\n'),
            ('output_csv_stream', '"n","Fibonacci Fn"\r\n0,0\r\n1,1\r\n'),
        ],
        ids=['simple', 'stream'],
    )
    def test_csv_output(self, asgi, app_kind, util, recipe, expected_head):
        module = util.load_module(
            recipe, parent_dir='examples/recipes', suffix=app_kind
        )
        app = util.create_app(asgi)
        app.add_route('/report', module.Report())

        result = falcon.testing.simulate_get(app, '/report')
        assert result.status_code == 200
        assert result.text.startswith(expected_head)


class TestPrettyJSON:
    class QuoteResource:
        def on_get(self, req, resp):
            resp.media = {
                'author': 'Grace Hopper',
                'quote': (
                    "I've always been more interested in the future than in the past."
                ),
            }

    class NegotiationMiddleware:
        def process_request(self, req, resp):
            resp.content_type = req.accept

    def test_optional_indent(self, util):
        recipe = util.load_module('examples/recipes/pretty_json_main.py')

        app = falcon.App(middleware=[self.NegotiationMiddleware()])
        app.add_route('/quote', self.QuoteResource())
        app.resp_options.media_handlers.update(
            {falcon.MEDIA_JSON: recipe.CustomJSONHandler()}
        )

        result = falcon.testing.simulate_get(
            app, '/quote', headers={'Accept': 'application/json; indent=4'}
        )
        assert result.status_code == 200
        assert result.text == (
            '{\n'
            '    "author": "Grace Hopper",\n'
            '    "quote": "I\'ve always been more interested in the future '
            'than in the past."\n'
            '}'
        )


class TestRawURLPath:
    def test_raw_path(self, asgi, app_kind, util):
        recipe = util.load_module(
            'raw_url_path', parent_dir='examples/recipes', suffix=app_kind
        )

        url1 = '/cache/http%3A%2F%2Ffalconframework.org'
        result1 = falcon.testing.simulate_get(recipe.app, url1)
        assert result1.status_code == 200
        assert result1.json == {'url': 'http://falconframework.org'}

        scope1 = falcon.testing.create_scope(url1)
        assert scope1['raw_path'] == url1.encode()

        url2 = '/cache/http%3A%2F%2Ffalconframework.org/status'
        result2 = falcon.testing.simulate_get(recipe.app, url2)
        assert result2.status_code == 200
        assert result2.json == {'cached': True}

        scope2 = falcon.testing.create_scope(url2)
        assert scope2['raw_path'] == url2.encode()


class TestTextPlainHandler:
    class MediaEcho:
        def on_post(self, req, resp):
            resp.content_type = req.content_type
            resp.media = req.get_media()

    def test_text_plain_basic(self, util):
        recipe = util.load_module('examples/recipes/plain_text_main.py')

        app = falcon.App()
        app.req_options.media_handlers['text/plain'] = recipe.TextHandler()
        app.resp_options.media_handlers['text/plain'] = recipe.TextHandler()

        app.add_route('/media', self.MediaEcho())

        client = falcon.testing.TestClient(app)
        payload = 'Hello, Falcon!'
        headers = {'Content-Type': 'text/plain'}
        response = client.simulate_post('/media', body=payload, headers=headers)

        assert response.status_code == 200
        assert response.content_type == 'text/plain'
        assert response.text == payload


class TestRequestIDContext:
    @pytest.fixture(params=['middleware', 'structlog'])
    def app(self, request, util, register_module):
        class RequestIDResource:
            def on_get(self, req, resp):
                # NOTE(vytas): Reference either ContextVar or req.context
                #   depending on the recipe being tested.
                context = getattr(recipe, 'ctx', req.context)
                resp.media = {'request_id': context.request_id}

        context = util.load_module(
            'examples/recipes/request_id_context.py', module_name='my_app.context'
        )
        # NOTE(vytas): Inject `context` into the importable system modules
        #   as it is referenced from other recipes.
        register_module('my_app.context', context)

        # NOTE(vytas): Inject a fake structlog module because we do not want to
        #   introduce a new test dependency for a single recipe.
        fake_structlog = types.ModuleType('structlog')
        fake_structlog.get_logger = unittest.mock.MagicMock()
        register_module('structlog', fake_structlog)

        recipe = util.load_module(f'examples/recipes/request_id_{request.param}.py')

        app = falcon.App(middleware=[recipe.RequestIDMiddleware()])
        app.add_route('/test', RequestIDResource())
        return app

    def test_request_id_persistence(self, app):
        client = falcon.testing.TestClient(app)

        resp1 = client.simulate_get('/test')
        request_id1 = resp1.json['request_id']

        resp2 = client.simulate_get('/test')
        request_id2 = resp2.json['request_id']

        assert request_id1 != request_id2

    def test_request_id_header(self, app):
        client = falcon.testing.TestClient(app)

        response = client.simulate_get('/test')
        assert 'X-Request-ID' in response.headers
        assert response.headers['X-Request-ID'] == response.json['request_id']


@pytest.mark.skipif(
    sys.version_info < (3, 9), reason='this recipe requires Python 3.9+'
)
class TestMsgspec:
    @pytest.fixture(scope='class', autouse=True)
    def msgspec(self):
        return pytest.importorskip(
            'msgspec', reason='this recipe requires msgspec [not found]'
        )

    def test_basic_media_handlers(self, asgi, util):
        class MediaResource:
            def on_post(self, req, resp):
                resp.content_type = falcon.MEDIA_TEXT
                resp.text = str(req.get_media())

            async def on_post_async(self, req, resp):
                resp.content_type = falcon.MEDIA_TEXT
                resp.text = str(await req.get_media())

        json_recipe = util.load_module('examples/recipes/msgspec_json_handler.py')
        msgpack_recipe = util.load_module('examples/recipes/msgspec_msgpack_handler.py')

        app = util.create_app(asgi)
        client = falcon.testing.TestClient(app)

        msgspec_handlers = {
            falcon.MEDIA_JSON: json_recipe.json_handler,
            falcon.MEDIA_MSGPACK: msgpack_recipe.msgpack_handler,
        }
        app.req_options.media_handlers.update(msgspec_handlers)
        app.resp_options.media_handlers.update(msgspec_handlers)

        suffix = 'async' if asgi else None
        app.add_route('/media', MediaResource(), suffix=suffix)

        resp0 = client.simulate_post(
            '/media', body=b'Hello: world', content_type=falcon.MEDIA_JSON
        )
        assert resp0.status_code == 400

        resp1 = client.simulate_post('/media', json=[1, 3, 3, 7])
        assert resp1.status_code == 200
        assert resp1.text == '[1, 3, 3, 7]'

        resp2 = client.simulate_post(
            '/media', body=b'\x94\x01\x03\x03\x07', content_type=falcon.MEDIA_MSGPACK
        )
        assert resp2.status_code == 200
        assert resp2.text == '[1, 3, 3, 7]'

        resp3 = client.simulate_get('/', headers={'Accept': falcon.MEDIA_JSON})
        assert resp3.status_code == 404
        assert resp3.json == {'title': '404 Not Found'}

        resp4 = client.simulate_get('/', headers={'Accept': falcon.MEDIA_MSGPACK})
        assert resp4.status_code == 404
        assert resp4.content == b'\x81\xa5title\xad404 Not Found'

    def test_validation_middleware(self, util, msgspec):
        mw_recipe = util.load_module('examples/recipes/msgspec_media_validation.py')

        class Metadata(msgspec.Struct):
            name: str

        class Resource:
            POST_SCHEMA = Metadata

            def on_post(self, req, resp, metadata):
                resp.media = msgspec.to_builtins(metadata)

        app = falcon.App(middleware=[mw_recipe.MsgspecMiddleware()])
        app.add_route('/meta', Resource())

        resp = falcon.testing.simulate_post(app, '/meta', json={'name': 'falcon'})
        assert resp.json == {'name': 'falcon'}

    def test_main_app(self, util):
        main_recipe = util.load_module('examples/recipes/msgspec_main.py')
        client = falcon.testing.TestClient(main_recipe.application)

        resp1 = client.simulate_post('/notes', json={'text': 'Test note'})
        assert resp1.status_code == 201
        created = resp1.json
        noteid = created['noteid']
        assert resp1.headers.get('Location') == f'/notes/{noteid}'

        resp2 = client.simulate_post('/notes', json={'note': 'Another'})
        assert resp2.status_code == 422

        resp3 = client.simulate_get('/notes')
        assert resp3.status_code == 200
        assert resp3.json == {noteid: created}

        resp4 = client.simulate_get(f'/notes/{noteid}')
        assert resp4.status_code == 200
        assert resp4.json == created

        resp5 = client.simulate_delete(f'/notes/{noteid}')
        assert resp5.status_code == 204

        resp6 = client.simulate_get(f'/notes/{noteid}')
        assert resp6.status_code == 404

        resp7 = client.simulate_get('/notes')
        assert resp7.status_code == 200
        assert resp7.json == {}
