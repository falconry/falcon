from argparse import Namespace
import io
import sys

import pytest

from falcon import App, inspect
from falcon.cmd import inspect_app
from falcon.testing import redirected

from _util import create_app  # NOQA

_WIN32 = sys.platform.startswith('win')
_MODULE = 'tests.test_cmd_inspect_app'


class DummyResource:

    def on_get(self, req, resp):
        resp.text = 'Test\n'
        resp.status = '200 OK'


class DummyResourceAsync:

    async def on_get(self, req, resp):
        resp.text = 'Test\n'
        resp.status = '200 OK'


def make_app(asgi=False):
    app = create_app(asgi)
    app.add_route('/test', DummyResourceAsync() if asgi else DummyResource())

    return app


_APP = make_app()


@pytest.fixture
def app(asgi):
    return make_app(asgi)


class TestMakeParser:
    @pytest.mark.parametrize('args, exp', (
        (['foo'], Namespace(app_module='foo', route_only=False, verbose=False, internal=False)),
        (
            ['foo', '-r'],
            Namespace(app_module='foo', route_only=True, verbose=False, internal=False)
        ),
        (
            ['foo', '--route_only'],
            Namespace(app_module='foo', route_only=True, verbose=False, internal=False)
        ),
        (
            ['foo', '-v'],
            Namespace(app_module='foo', route_only=False, verbose=True, internal=False)
        ),
        (
            ['foo', '--verbose'],
            Namespace(app_module='foo', route_only=False, verbose=True, internal=False)
        ),
        (
            ['foo', '-i'],
            Namespace(app_module='foo', route_only=False, verbose=False, internal=True)
        ),
        (
            ['foo', '--internal'],
            Namespace(app_module='foo', route_only=False, verbose=False, internal=True)
        ),
        (
            ['foo', '-r', '-v', '-i'],
            Namespace(app_module='foo', route_only=True, verbose=True, internal=True)
        ),
    ))
    def test_make_parser(self, args, exp):
        parser = inspect_app.make_parser()
        actual = parser.parse_args(args)
        assert actual == exp

    def test_make_parser_error(self):
        parser = inspect_app.make_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])


class TestLoadApp:
    @pytest.mark.parametrize('name', ('_APP', 'make_app'))
    def test_load_app(self, name):
        parser = inspect_app.make_parser()
        args = Namespace(app_module='{}:{}'.format(_MODULE, name), route_only=False, verbose=False)
        app = inspect_app.load_app(parser, args)
        assert isinstance(app, App)
        assert app._router.find('/test') is not None

    @pytest.mark.parametrize('name', (
        'foo',  # not exists
        '_MODULE',  # not callable and not app
        'DummyResource',  # callable and not app
    ))
    def test_load_app_error(self, name):
        parser = inspect_app.make_parser()
        args = Namespace(app_module='{}:{}'.format(_MODULE, name), route_only=False, verbose=False)
        with pytest.raises(SystemExit):
            inspect_app.load_app(parser, args)

    def test_load_app_module_error(self):
        parser = inspect_app.make_parser()
        args = Namespace(app_module='foo', route_only=False, verbose=False)
        with pytest.raises(SystemExit):
            inspect_app.load_app(parser, args)


@pytest.mark.skipif(sys.version_info < (3, 6), reason='dict order is not stable')
@pytest.mark.parametrize('verbose', (True, False), ids=['verbose', 'not-verbose'])
@pytest.mark.parametrize('internal', (True, False), ids=['internal', 'not-internal'])
class TestMain:
    def check(self, actual, expect):
        if _WIN32:
            # windows randomly returns the driver name as lowercase
            assert actual.casefold() == expect.casefold()
        else:
            assert actual == expect

    def test_routes_only(self, verbose, internal, monkeypatch):
        args = ['some-file.py', '{}:{}'.format(_MODULE, '_APP'), '-r']
        if verbose:
            args.append('-v')
        if internal:
            args.append('-i')
        monkeypatch.setattr('sys.argv', args)
        output = io.StringIO()
        with redirected(stdout=output):
            inspect_app.main()
        routes = inspect.inspect_routes(_APP)
        sv = inspect.StringVisitor(verbose, internal)
        expect = '\n'.join([sv.process(r) for r in routes])
        self.check(output.getvalue().strip(), expect)

    def test_inspect(self, verbose, internal, monkeypatch):
        args = ['some-file.py', '{}:{}'.format(_MODULE, '_APP')]
        if verbose:
            args.append('-v')
        if internal:
            args.append('-i')
        monkeypatch.setattr('sys.argv', args)
        output = io.StringIO()
        with redirected(stdout=output):
            inspect_app.main()
        ins = inspect.inspect_app(_APP)
        self.check(output.getvalue().strip(), ins.to_string(verbose, internal))


def test_route_main(monkeypatch):
    called = False

    def mock():
        nonlocal called
        called = True

    monkeypatch.setattr(inspect_app, 'main', mock)
    output = io.StringIO()
    with redirected(stdout=output):
        inspect_app.route_main()

    assert 'deprecated' in output.getvalue()
    assert called
