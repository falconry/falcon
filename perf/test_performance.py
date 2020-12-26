import pytest


@pytest.mark.asgi
def test_asgi_metric(gauge):
    gauge('asgi')


@pytest.mark.hello
def test_hello_metric(gauge):
    gauge('hello')


@pytest.mark.media
def test_media_metric(gauge):
    gauge('media')


@pytest.mark.query
def test_query_metric(gauge):
    gauge('query')
