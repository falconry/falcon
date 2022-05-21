import pytest

from falcon.request import Request
import falcon.testing as testing

from _util import create_req  # NOQA


def test_remote_addr_default(asgi):
    req = create_req(asgi)
    assert req.remote_addr == '127.0.0.1'


def test_remote_addr_non_default(asgi):
    client_ip = '10.132.0.5'
    req = create_req(asgi, remote_addr=client_ip)
    assert req.remote_addr == client_ip


def test_remote_addr_only(asgi):
    req = create_req(
        asgi,
        host='example.com',
        path='/access_route',
        headers={
            'Forwarded': (
                'for=192.0.2.43, for="[2001:db8:cafe::17]:555",'
                'for="unknown", by=_hidden,for="\\"\\\\",'
                'for="198\\.51\\.100\\.17\\:1236";'
                'proto=https;host=example.com'
            )
        },
    )

    assert req.remote_addr == '127.0.0.1'


def test_rfc_forwarded(asgi):
    req = create_req(
        asgi,
        host='example.com',
        path='/access_route',
        headers={
            'Forwarded': (
                'for=192.0.2.43,for=,'
                'for="[2001:db8:cafe::17]:555",'
                'for=x,'
                'for="unknown", by=_hidden,for="\\"\\\\",'
                'for="_don\\"t_\\try_this\\\\at_home_\\42",'
                'for="198\\.51\\.100\\.17\\:1236";'
                'proto=https;host=example.com'
            )
        },
    )

    compares = [
        '192.0.2.43',
        '2001:db8:cafe::17',
        'x',
        'unknown',
        '"\\',
        '_don"t_try_this\\at_home_42',
        '198.51.100.17',
        '127.0.0.1',
    ]

    assert req.access_route == compares

    # test cached
    assert req.access_route == compares


def test_malformed_rfc_forwarded(asgi):
    req = create_req(
        asgi, host='example.com', path='/access_route', headers={'Forwarded': 'for'}
    )

    assert req.access_route == ['127.0.0.1']

    # test cached
    assert req.access_route == ['127.0.0.1']


@pytest.mark.parametrize('include_localhost', [True, False])
def test_x_forwarded_for(asgi, include_localhost):

    forwarded_for = '192.0.2.43, 2001:db8:cafe::17,unknown, _hidden, 203.0.113.60'

    if include_localhost:
        forwarded_for += ', 127.0.0.1'

    req = create_req(
        asgi,
        host='example.com',
        path='/access_route',
        headers={'X-Forwarded-For': forwarded_for},
    )

    assert req.access_route == [
        '192.0.2.43',
        '2001:db8:cafe::17',
        'unknown',
        '_hidden',
        '203.0.113.60',
        '127.0.0.1',
    ]


def test_x_real_ip(asgi):
    req = create_req(
        asgi,
        host='example.com',
        path='/access_route',
        headers={'X-Real-IP': '2001:db8:cafe::17'},
    )

    assert req.access_route == ['2001:db8:cafe::17', '127.0.0.1']


@pytest.mark.parametrize('remote_addr', ['10.0.0.1', '98.245.211.177'])
def test_remote_addr(asgi, remote_addr):
    req = create_req(
        asgi,
        host='example.com',
        path='/access_route',
        remote_addr=remote_addr,
    )

    assert req.access_route == [remote_addr]


def test_remote_addr_missing():
    env = testing.create_environ(host='example.com', path='/access_route')

    # NOTE(kgriffs): It should not be present, but include this check so
    #   that in the future if things change, we still cover this case.
    if 'REMOTE_ADDR' in env:
        del env['REMOTE_ADDR']

    req = Request(env)
    assert req.access_route == ['127.0.0.1']
