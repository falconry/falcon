from unittest.mock import MagicMock

import pytest

from falcon.routing import CompiledRouter, CompiledRouterOptions


def test_ctor_options():
    options = CompiledRouterOptions()

    router = CompiledRouter(_options=options)

    assert router.options is options
    assert router._converter_map is options.converters.data


def test_find_src(monkeypatch):
    called = False
    find = CompiledRouter.find

    def mock(*args):
        nonlocal called
        called = True
        find(*args)

    monkeypatch.setattr(CompiledRouter, 'find', mock)
    router = CompiledRouter()

    assert router.finder_src is not None
    assert called


@pytest.fixture
def patch_add_route(monkeypatch):
    add_route = CompiledRouter.add_route
    mock = MagicMock(side_effect=lambda *a, **k: add_route(router, *a, **k))
    monkeypatch.setattr(CompiledRouter, 'add_route', mock)
    router = CompiledRouter()
    return mock, router


@pytest.mark.parametrize(
    'kwargs',
    (
        {},
        {'compile': False},
        {'compile': False, 'suffix': 'other'},
        {'suffix': 'other'},
    ),
)
def test_no_compile_kw(patch_add_route, kwargs):
    mock, router = patch_add_route

    res = MockResource()
    router.add_route('/foo', res, **kwargs)
    other = kwargs.copy()
    other['compile'] = True
    assert mock.call_count == 2
    mock.assert_has_calls(((('/foo', res), kwargs), (('/foo', res), other)))
    assert router._find == router._compile_and_find


def test_compile(patch_add_route):
    mock, router = patch_add_route

    res = MockResource()
    router.add_route('/foo', res, compile=True)
    mock.assert_called_once()
    assert router._find != router._compile_and_find


def test_verify_route_on_add(patch_add_route):
    mock, router = patch_add_route

    router.options.verify_route_on_add = False

    res = MockResource()
    router.add_route('/foo', res)
    mock.assert_called_once()
    assert router._find == router._compile_and_find


class MockResource:
    def on_get(self, req, res):
        pass

    def on_get_other(self, req, res):
        pass
