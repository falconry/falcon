import pytest

from falcon.request import Request
import falcon.testing as testing


def test_no_forwarded_headers():
    req = Request(testing.create_environ(
        host='example.com',
        path='/languages',
        app='backoffice'
    ))

    assert req.forwarded is None
    assert req.forwarded_uri == req.uri
    assert req.forwarded_uri == 'http://example.com/backoffice/languages'
    assert req.forwarded_prefix == 'http://example.com/backoffice'


def test_x_forwarded_host():
    req = Request(testing.create_environ(
        host='suchproxy.suchtesting.com',
        path='/languages',
        headers={'X-Forwarded-Host': 'something.org'}
    ))

    assert req.forwarded is None
    assert req.forwarded_host == 'something.org'
    assert req.forwarded_uri != req.uri
    assert req.forwarded_uri == 'http://something.org/languages'
    assert req.forwarded_prefix == 'http://something.org'
    assert req.forwarded_prefix == 'http://something.org'  # Check cached value


def test_x_forwarded_proto():
    req = Request(testing.create_environ(
        host='example.org',
        path='/languages',
        headers={'X-Forwarded-Proto': 'HTTPS'}
    ))

    assert req.forwarded is None
    assert req.forwarded_scheme == 'https'
    assert req.forwarded_uri != req.uri
    assert req.forwarded_uri == 'https://example.org/languages'
    assert req.forwarded_prefix == 'https://example.org'


def test_forwarded_host():
    req = Request(testing.create_environ(
        host='suchproxy02.suchtesting.com',
        path='/languages',
        headers={
            'Forwarded': 'host=something.org , host=suchproxy01.suchtesting.com'
        }
    ))

    assert req.forwarded is not None
    for f in req.forwarded:
        assert f.src is None
        assert f.dest is None
        assert f.scheme is None

    assert req.forwarded[0].host == 'something.org'
    assert req.forwarded[1].host == 'suchproxy01.suchtesting.com'

    assert req.forwarded_host == 'something.org'
    assert req.forwarded_uri != req.uri
    assert req.forwarded_uri == 'http://something.org/languages'
    assert req.forwarded_prefix == 'http://something.org'


def test_forwarded_multiple_params():
    req = Request(testing.create_environ(
        host='suchproxy02.suchtesting.com',
        path='/languages',
        headers={
            'Forwarded': (
                'host=something.org;proto=hTTps;ignore=me;for=108.166.30.185, '
                'by=203.0.113.43;host=suchproxy01.suchtesting.com;proto=httP'
            )
        }
    ))

    assert req.forwarded is not None

    assert req.forwarded[0].host == 'something.org'
    assert req.forwarded[0].scheme == 'https'
    assert req.forwarded[0].src == '108.166.30.185'
    assert req.forwarded[0].dest is None

    assert req.forwarded[1].host == 'suchproxy01.suchtesting.com'
    assert req.forwarded[1].scheme == 'http'
    assert req.forwarded[1].src is None
    assert req.forwarded[1].dest == '203.0.113.43'

    assert req.forwarded_scheme == 'https'
    assert req.forwarded_host == 'something.org'
    assert req.forwarded_uri != req.uri
    assert req.forwarded_uri == 'https://something.org/languages'
    assert req.forwarded_prefix == 'https://something.org'


def test_forwarded_missing_first_hop_host():
    req = Request(testing.create_environ(
        host='suchproxy02.suchtesting.com',
        path='/languages',
        app='doge',
        headers={
            'Forwarded': 'for=108.166.30.185,host=suchproxy01.suchtesting.com'
        }
    ))

    assert req.forwarded[0].host is None
    assert req.forwarded[0].src == '108.166.30.185'

    assert req.forwarded[1].host == 'suchproxy01.suchtesting.com'
    assert req.forwarded[1].src is None

    assert req.forwarded_scheme == 'http'
    assert req.forwarded_host == 'suchproxy02.suchtesting.com'
    assert req.forwarded_uri == req.uri
    assert req.forwarded_uri == 'http://suchproxy02.suchtesting.com/doge/languages'
    assert req.forwarded_prefix == 'http://suchproxy02.suchtesting.com/doge'


def test_forwarded_quote_escaping():
    req = Request(testing.create_environ(
        host='suchproxy02.suchtesting.com',
        path='/languages',
        app='doge',
        headers={
            'Forwarded': 'for="1\\.2\\.3\\.4";some="extra,\\"info\\""'
        }
    ))

    assert req.forwarded[0].host is None
    assert req.forwarded[0].src == '1.2.3.4'


@pytest.mark.parametrize('forwarded, expected_dest', [
    ('for=1.2.3.4;by="', None),
    ('for=1.2.3.4;by=4\\.3.2.1thing=blah', '4'),
    ('for=1.2.3.4;by="\\4.3.2.1"thing=blah', '4.3.2.1'),
    ('for=1.2.3.4;by="4.3.2.\\1"thing="blah"', '4.3.2.1'),
    ('for=1.2.3.4;by="4.3.\\2\\.1" thing="blah"', '4.3.2.1'),
])
def test_escape_malformed_requests(forwarded, expected_dest):

    req = Request(testing.create_environ(
        host='suchproxy02.suchtesting.com',
        path='/languages',
        app='doge',
        headers={
            'Forwarded': forwarded
        }
    ))

    assert len(req.forwarded) == 1
    assert req.forwarded[0].src == '1.2.3.4'
    assert req.forwarded[0].dest == expected_dest
