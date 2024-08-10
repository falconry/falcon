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
                    "I've always been more interested in "
                    'the future than in the past.'
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
    def path_extras(self, asgi, url):
        if asgi:
            return {'raw_path': url.encode()}
        return None

    def test_raw_path(self, asgi, app_kind, util):
        recipe = util.load_module(
            'raw_url_path', parent_dir='examples/recipes', suffix=app_kind
        )

        # TODO(vytas): Improve TestClient to automatically add ASGI raw_path
        #   (as it does for WSGI): GH #2262.

        url1 = '/cache/http%3A%2F%2Ffalconframework.org'
        result1 = falcon.testing.simulate_get(
            recipe.app, url1, extras=self.path_extras(asgi, url1)
        )
        assert result1.status_code == 200
        assert result1.json == {'url': 'http://falconframework.org'}

        url2 = '/cache/http%3A%2F%2Ffalconframework.org/status'
        result2 = falcon.testing.simulate_get(
            recipe.app, url2, extras=self.path_extras(asgi, url2)
        )
        assert result2.status_code == 200
        assert result2.json == {'cached': True}
