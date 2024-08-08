import pathlib

import pytest

import falcon
import falcon.testing


@pytest.fixture()
def recipe_module(example_module):
    def load(filename):
        path = pathlib.Path('recipes') / filename
        return example_module(path, prefix='examples.recipes')

    return load


class TestOutputCSV:
    @pytest.mark.parametrize(
        'recipe,expected_head',
        [
            ('output_csv_text', '"fruit","quantity"\r\n"apples",13\r\n'),
            ('output_csv_stream', '"n","Fibonacci Fn"\r\n0,0\r\n1,1\r\n'),
        ],
        ids=['simple', 'stream'],
    )
    def test_csv_output(self, asgi, create_app, recipe_module, recipe, expected_head):
        suffix = 'asgi' if asgi else 'wsgi'
        loaded = recipe_module(f'{recipe}_{suffix}.py')
        app = create_app()
        app.add_route('/report', loaded.Report())

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

    def test_optional_indent(self, create_app, recipe_module):
        recipe = recipe_module('pretty_json_main.py')

        app = create_app(middleware=[self.NegotiationMiddleware()])
        (app.add_route('/quote', self.QuoteResource()),)
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
