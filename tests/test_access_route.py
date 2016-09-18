from falcon.request import Request
import falcon.testing as testing


def test_remote_addr_only():
    req = Request(testing.create_environ(
        host='example.com',
        path='/access_route',
        headers={
            'Forwarded': ('for=192.0.2.43, for="[2001:db8:cafe::17]:555",'
                          'for="unknown", by=_hidden,for="\\"\\\\",'
                          'for="198\\.51\\.100\\.17\\:1236";'
                          'proto=https;host=example.com')
        }))

    assert req.remote_addr == '127.0.0.1'


def test_rfc_forwarded():
    req = Request(testing.create_environ(
        host='example.com',
        path='/access_route',
        headers={
            'Forwarded': ('for=192.0.2.43,for=,'
                          'for="[2001:db8:cafe::17]:555",'
                          'for=x,'
                          'for="unknown", by=_hidden,for="\\"\\\\",'
                          'for="_don\\\"t_\\try_this\\\\at_home_\\42",'
                          'for="198\\.51\\.100\\.17\\:1236";'
                          'proto=https;host=example.com')
        }))

    compares = ['192.0.2.43', '2001:db8:cafe::17', 'x',
                'unknown', '"\\', '_don"t_try_this\\at_home_42',
                '198.51.100.17']

    req.access_route == compares

    # test cached
    req.access_route == compares


def test_malformed_rfc_forwarded():
    req = Request(testing.create_environ(
        host='example.com',
        path='/access_route',
        headers={
            'Forwarded': 'for'
        }))

    req.access_route == []

    # test cached
    req.access_route == []


def test_x_forwarded_for():
    req = Request(testing.create_environ(
        host='example.com',
        path='/access_route',
        headers={
            'X-Forwarded-For': ('192.0.2.43, 2001:db8:cafe::17,'
                                'unknown, _hidden, 203.0.113.60')
        }))

    assert req.access_route == [
        '192.0.2.43',
        '2001:db8:cafe::17',
        'unknown',
        '_hidden',
        '203.0.113.60'
    ]


def test_x_real_ip():
    req = Request(testing.create_environ(
        host='example.com',
        path='/access_route',
        headers={
            'X-Real-IP': '2001:db8:cafe::17'
        }))

    assert req.access_route == ['2001:db8:cafe::17']


def test_remote_addr():
    req = Request(testing.create_environ(
        host='example.com',
        path='/access_route'))

    assert req.access_route == ['127.0.0.1']


def test_remote_addr_missing():
    env = testing.create_environ(host='example.com', path='/access_route')
    del env['REMOTE_ADDR']

    req = Request(env)
    assert req.access_route == []
