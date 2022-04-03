from threading import Barrier, Thread
from time import sleep
from unittest.mock import MagicMock

import pytest

from falcon.routing import CompiledRouter


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

    assert mock.call_count == 1
    mock.assert_has_calls(((('/foo', res), kwargs),))
    assert router._find == router._compile_and_find


def test_compile(patch_add_route):
    mock, router = patch_add_route

    res = MockResource()
    router.add_route('/foo', res, compile=True)
    assert mock.call_count == 1
    assert router._find != router._compile_and_find


def test_add_route_after_first_request():
    router = CompiledRouter()

    router.add_route('/foo', MockResource())
    assert router.find('/foo') is not None
    assert router._find != router._compile_and_find

    router.add_route('/bar', MockResource(), suffix='other')
    assert router._find == router._compile_and_find
    assert router.find('/bar') is not None
    assert router._find != router._compile_and_find


def test_multithread_compile(monkeypatch):
    def side_effect():
        sleep(0.05)
        return lambda *args: None

    mock = MagicMock(side_effect=side_effect)
    monkeypatch.setattr(CompiledRouter, '_compile', mock)

    router = CompiledRouter()
    mr = MockResource()

    router.add_route('/foo', mr)

    calls = 0
    num_threads = 3
    barrier = Barrier(num_threads)

    def find():
        nonlocal calls
        barrier.wait()
        assert router.find('/foo') is None
        calls += 1

    threads = [Thread(target=find) for i in range(num_threads)]
    for t in threads:
        t.start()

    for t in threads:
        t.join()

    assert calls == 3
    mock.assert_called_once_with()


class MockResource:
    def on_get(self, req, res):
        pass

    def on_get_other(self, req, res):
        pass
