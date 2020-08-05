import pytest

import falcon
import falcon.errors as errors
import falcon.status_codes as status
from falcon.util.deprecation import DeprecatedWarning


@pytest.mark.parametrize('err, title', [
    (falcon.HTTPBadRequest, status.HTTP_400),
    (falcon.HTTPUnauthorized, status.HTTP_401),
    (falcon.HTTPForbidden, status.HTTP_403),
    (falcon.HTTPNotFound, status.HTTP_404),
    (errors.HTTPRouteNotFound, status.HTTP_404),
    (falcon.HTTPNotAcceptable, status.HTTP_406),
    (falcon.HTTPConflict, status.HTTP_409),
    (falcon.HTTPGone, status.HTTP_410),
    (falcon.HTTPLengthRequired, status.HTTP_411),
    (falcon.HTTPPreconditionFailed, status.HTTP_412),
    (falcon.HTTPPayloadTooLarge, status.HTTP_413),
    (falcon.HTTPUriTooLong, status.HTTP_414),
    (falcon.HTTPUnsupportedMediaType, status.HTTP_415),
    (falcon.HTTPUnprocessableEntity, status.HTTP_422),
    (falcon.HTTPLocked, status.HTTP_423),
    (falcon.HTTPFailedDependency, status.HTTP_424),
    (falcon.HTTPPreconditionRequired, status.HTTP_428),
    (falcon.HTTPTooManyRequests, status.HTTP_429),
    (falcon.HTTPRequestHeaderFieldsTooLarge, status.HTTP_431),
    (falcon.HTTPUnavailableForLegalReasons, status.HTTP_451),
    (falcon.HTTPInternalServerError, status.HTTP_500),
    (falcon.HTTPNotImplemented, status.HTTP_501),
    (falcon.HTTPBadGateway, status.HTTP_502),
    (falcon.HTTPServiceUnavailable, status.HTTP_503),
    (falcon.HTTPGatewayTimeout, status.HTTP_504),
    (falcon.HTTPVersionNotSupported, status.HTTP_505),
    (falcon.HTTPInsufficientStorage, status.HTTP_507),
    (falcon.HTTPLoopDetected, status.HTTP_508),
    (falcon.HTTPNetworkAuthenticationRequired, status.HTTP_511),
])
def test_with_default_title_and_desc(err, title):
    with pytest.raises(err) as e:
        raise err()

    assert e.value.title == title
    assert e.value.description is None

    if e.value.headers:
        assert 'Retry-After' not in e.value.headers


@pytest.mark.parametrize('err, title, args', (
    (falcon.HTTPMethodNotAllowed, status.HTTP_405, (['GET'], )),
    (falcon.HTTPRangeNotSatisfiable, status.HTTP_416, (11,)),
))
def test_with_default_title_and_desc_args(err, title, args):
    with pytest.raises(err) as e:
        raise err(*args)

    assert e.value.title == title
    assert e.value.description is None

    if e.value.headers:
        assert 'Retry-After' not in e.value.headers


@pytest.mark.parametrize('err', [
    falcon.HTTPBadRequest,
    falcon.HTTPUnauthorized,
    falcon.HTTPForbidden,
    falcon.HTTPNotFound,
    errors.HTTPRouteNotFound,
    falcon.HTTPNotAcceptable,
    falcon.HTTPConflict,
    falcon.HTTPGone,
    falcon.HTTPLengthRequired,
    falcon.HTTPPreconditionFailed,
    falcon.HTTPPayloadTooLarge,
    falcon.HTTPUriTooLong,
    falcon.HTTPUnsupportedMediaType,
    falcon.HTTPUnprocessableEntity,
    falcon.HTTPLocked,
    falcon.HTTPFailedDependency,
    falcon.HTTPPreconditionRequired,
    falcon.HTTPTooManyRequests,
    falcon.HTTPRequestHeaderFieldsTooLarge,
    falcon.HTTPUnavailableForLegalReasons,
    falcon.HTTPInternalServerError,
    falcon.HTTPNotImplemented,
    falcon.HTTPBadGateway,
    falcon.HTTPServiceUnavailable,
    falcon.HTTPGatewayTimeout,
    falcon.HTTPVersionNotSupported,
    falcon.HTTPInsufficientStorage,
    falcon.HTTPLoopDetected,
    falcon.HTTPNetworkAuthenticationRequired,
])
def test_with_title_desc_and_headers(err):
    title = 'trace'
    desc = 'boom'
    headers = {'foo': 'bar'}

    with pytest.raises(err) as e:
        raise err(title=title, description=desc, headers=headers)

    assert e.value.title == title
    assert e.value.description == desc
    assert e.value.headers['foo'] == 'bar'


@pytest.mark.parametrize('err', [
    falcon.HTTPBadRequest,
    falcon.HTTPUnauthorized,
    falcon.HTTPForbidden,
    falcon.HTTPNotFound,
    errors.HTTPRouteNotFound,
    falcon.HTTPNotAcceptable,
    falcon.HTTPConflict,
    falcon.HTTPGone,
    falcon.HTTPLengthRequired,
    falcon.HTTPPreconditionFailed,
    falcon.HTTPPayloadTooLarge,
    falcon.HTTPUriTooLong,
    falcon.HTTPUnsupportedMediaType,
    falcon.HTTPUnprocessableEntity,
    falcon.HTTPLocked,
    falcon.HTTPFailedDependency,
    falcon.HTTPPreconditionRequired,
    falcon.HTTPTooManyRequests,
    falcon.HTTPRequestHeaderFieldsTooLarge,
    falcon.HTTPUnavailableForLegalReasons,
    falcon.HTTPInternalServerError,
    falcon.HTTPNotImplemented,
    falcon.HTTPBadGateway,
    falcon.HTTPServiceUnavailable,
    falcon.HTTPGatewayTimeout,
    falcon.HTTPVersionNotSupported,
    falcon.HTTPInsufficientStorage,
    falcon.HTTPLoopDetected,
    falcon.HTTPNetworkAuthenticationRequired,
])
def test_kw_only(err):
    # only deprecated for now
    # with pytest.raises(TypeError, match='positional argument'):
    #     err('foo', 'bar')
    with pytest.warns(DeprecatedWarning, match='positional args are deprecated'):
        err('foo', 'bar')


@pytest.mark.parametrize('err, args', (
    (falcon.HTTPMethodNotAllowed, (['GET'], )),
    (falcon.HTTPRangeNotSatisfiable, (11,)),
))
def test_with_title_desc_and_headers_args(err, args):
    title = 'trace'
    desc = 'boom'
    headers = {'foo': 'bar'}

    with pytest.raises(err) as e:
        raise err(*args, title=title, description=desc, headers=headers)

    assert e.value.title == title
    assert e.value.description == desc
    assert e.value.headers['foo'] == 'bar'


@pytest.mark.parametrize('err, args', (
    (falcon.HTTPMethodNotAllowed, (['GET'], )),
    (falcon.HTTPRangeNotSatisfiable, (11,)),
    (falcon.HTTPInvalidHeader, ('foo', 'bar')),
    (falcon.HTTPMissingHeader, ('foo',)),
    (falcon.HTTPInvalidParam, ('foo', 'bar')),
    (falcon.HTTPMissingParam, ('foo',)),
))
def test_args_kw_only(err, args):
    # only deprecated for now
    # with pytest.raises(TypeError, match='positional argument'):
    #     err(*args, 'bar')
    with pytest.warns(DeprecatedWarning, match='positional args are deprecated'):
        err(*args, 'bar')


@pytest.mark.parametrize('err', [
    falcon.HTTPServiceUnavailable,
    falcon.HTTPTooManyRequests,
    falcon.HTTPPayloadTooLarge,
])
def test_with_retry_after(err):
    with pytest.raises(err) as e:
        raise err(retry_after='123')

    assert e.value.headers['Retry-After'] == '123'


@pytest.mark.parametrize('err', [
    falcon.HTTPServiceUnavailable,
    falcon.HTTPTooManyRequests,
    falcon.HTTPPayloadTooLarge,
])
def test_with_retry_after_and_headers(err):
    with pytest.raises(err) as e:
        raise err(retry_after='123', headers={'foo': 'bar'})

    assert e.value.headers['Retry-After'] == '123'
    assert e.value.headers['foo'] == 'bar'


def test_http_error_repr():
    error = falcon.HTTPBadRequest()
    _repr = '<%s: %s>' % (error.__class__.__name__, error.status)
    assert error.__repr__() == _repr


@pytest.mark.parametrize('err, args, title, desc', (
    (falcon.HTTPInvalidHeader, ('foo', 'bar'), 'Invalid header value',
     'The value provided for the "bar" header is invalid. foo'),
    (falcon.HTTPMissingHeader, ('foo',), 'Missing header value', 'The "foo" header is required.'),
    (falcon.HTTPInvalidParam, ('foo', 'bar'), 'Invalid parameter',
     'The "bar" parameter is invalid. foo'),
    (falcon.HTTPMissingParam, ('foo',), 'Missing parameter', 'The "foo" parameter is required.'),
))
def test_custom_400(err, args, title, desc):
    with pytest.raises(err) as e:
        raise err(*args)

    assert e.value.title == title
    assert e.value.description == desc


@pytest.mark.parametrize('err, header_name, kw_name, args, res, kw_required', (
    (falcon.HTTPUnauthorized, 'WWW-Authenticate', 'challenges', ('a', 'b'), 'a, b', False),
    (falcon.HTTPMethodNotAllowed, 'Allow', 'allowed_methods', ('a', 'b'), 'a, b', True),
    (falcon.HTTPPayloadTooLarge, 'Retry-After', 'retry_after', 123, '123', False),
    (falcon.HTTPRangeNotSatisfiable, 'Content-Range', 'resource_length', 123, 'bytes */123', True),
    (falcon.HTTPTooManyRequests, 'Retry-After', 'retry_after', 123, '123', False),
    (falcon.HTTPServiceUnavailable, 'Retry-After', 'retry_after', 123, '123', False),
))
class TestErrorsWithHeadersKW:
    def test_no_header(self, err, header_name, kw_name, args, res, kw_required):
        if not kw_required:
            value = err()

            if value.headers:
                assert header_name not in value.headers

    def test_other_header(self, err, header_name, kw_name, args, res, kw_required):
        headers = {'foo bar': 'baz'}
        kw = {kw_name: args}
        value = err(**kw, headers=headers)

        assert value.headers['foo bar'] == 'baz'
        assert header_name in value.headers
        assert value.headers[header_name] == res

    def test_override_header(self, err, header_name, kw_name, args, res, kw_required):
        headers = {'foo bar': 'baz', header_name: 'other'}
        kw = {kw_name: args}
        value = err(**kw, headers=headers)

        assert value.headers['foo bar'] == 'baz'
        assert header_name in value.headers
        assert value.headers[header_name] == res

    def test_other_header_list(self, err, header_name, kw_name, args, res, kw_required):
        headers = [('foo bar', 'baz')]
        kw = {kw_name: args}
        value = err(**kw, headers=headers)

        assert value.headers['foo bar'] == 'baz'
        assert header_name in value.headers
        assert isinstance(value.headers, dict)
        assert value.headers[header_name] == res

    def test_override_header_list(self, err, header_name, kw_name, args, res, kw_required):
        headers = [('foo bar', 'baz'), (header_name, 'other')]
        kw = {kw_name: args}
        value = err(**kw, headers=headers)

        assert value.headers['foo bar'] == 'baz'
        assert header_name in value.headers
        assert isinstance(value.headers, dict)
        assert value.headers[header_name] == res
