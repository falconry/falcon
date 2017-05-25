import falcon
import falcon.status_codes as status


def test_http_bad_request_no_title_and_desc():
    try:
        raise falcon.HTTPBadRequest()
    except falcon.HTTPBadRequest as e:
        assert status.HTTP_400 == e.title
        assert e.description is None


def test_http_bad_request_with_title_and_desc():
    try:
        raise falcon.HTTPBadRequest(title='Test', description='Testdescription')
    except falcon.HTTPBadRequest as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_unauthorized_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPUnauthorized()
    except falcon.HTTPUnauthorized as e:
        assert status.HTTP_401 == e.title
        assert e.description is None
        assert 'WWW-Authenticate' not in e.headers


def test_http_unauthorized_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPUnauthorized(
            title='Test',
            description='Testdescription',
            challenges=['Testch']
        )
    except falcon.HTTPUnauthorized as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description
        assert 'Testch' == e.headers['WWW-Authenticate']


def test_http_forbidden_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPForbidden()
    except falcon.HTTPForbidden as e:
        assert status.HTTP_403 == e.title
        assert e.description is None


def test_http_forbidden_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPForbidden(title='Test', description='Testdescription')
    except falcon.HTTPForbidden as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_not_acceptable_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPNotAcceptable()
    except falcon.HTTPNotAcceptable as e:
        assert e.description is None


def test_http_not_acceptable_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPNotAcceptable(description='Testdescription')
    except falcon.HTTPNotAcceptable as e:
        assert 'Testdescription' == e.description


def test_http_conflict_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPConflict()
    except falcon.HTTPConflict as e:
        assert status.HTTP_409 == e.title
        assert e.description is None


def test_http_conflict_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPConflict(title='Test', description='Testdescription')
    except falcon.HTTPConflict as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_length_required_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPLengthRequired()
    except falcon.HTTPLengthRequired as e:
        assert status.HTTP_411 == e.title
        assert e.description is None


def test_http_length_required_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPLengthRequired(title='Test', description='Testdescription')
    except falcon.HTTPLengthRequired as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_precondition_failed_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPPreconditionFailed()
    except falcon.HTTPPreconditionFailed as e:
        assert status.HTTP_412 == e.title
        assert e.description is None


def test_http_precondition_failed_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPPreconditionFailed(title='Test', description='Testdescription')
    except falcon.HTTPPreconditionFailed as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_request_entity_too_large_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPRequestEntityTooLarge()
    except falcon.HTTPRequestEntityTooLarge as e:
        assert status.HTTP_413 == e.title
        assert e.description is None
        assert 'Retry-After' not in e.headers


def test_http_request_entity_too_large_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPRequestEntityTooLarge(
            title='Test',
            description='Testdescription',
            retry_after=123
        )
    except falcon.HTTPRequestEntityTooLarge as e:
        assert 'Test' == e.title, 'Title should be "Test"'
        assert 'Testdescription' == e.description
        assert '123' == e.headers['Retry-After']


def test_http_uri_too_long_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPUriTooLong()
    except falcon.HTTPUriTooLong as e:
        assert status.HTTP_414 == e.title
        assert e.description is None


def test_http_uri_too_long_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPUriTooLong(title='Test', description='Testdescription')
    except falcon.HTTPUriTooLong as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_unsupported_media_type_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPUnsupportedMediaType()
    except falcon.HTTPUnsupportedMediaType as e:
        assert e.description is None


def test_http_unsupported_media_type_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPUnsupportedMediaType(description='Testdescription')
    except falcon.HTTPUnsupportedMediaType as e:
        assert 'Testdescription' == e.description


def test_http_unprocessable_entity_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPUnprocessableEntity()
    except falcon.HTTPUnprocessableEntity as e:
        assert status.HTTP_422 == e.title
        assert e.description is None


def test_http_unprocessable_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPUnprocessableEntity(title='Test', description='Testdescription')
    except falcon.HTTPUnprocessableEntity as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_locked_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPLocked()
    except falcon.HTTPLocked as e:
        assert status.HTTP_423 == e.title
        assert e.description is None


def test_http_locked_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPLocked(title='Test', description='Testdescription')
    except falcon.HTTPLocked as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_failed_dependency_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPFailedDependency()
    except falcon.HTTPFailedDependency as e:
        assert status.HTTP_424 == e.title
        assert e.description is None


def test_http_failed_dependency_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPFailedDependency(title='Test', description='Testdescription')
    except falcon.HTTPFailedDependency as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_precondition_required_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPPreconditionRequired()
    except falcon.HTTPPreconditionRequired as e:
        assert status.HTTP_428 == e.title
        assert e.description is None


def test_http_precondition_required_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPPreconditionRequired(title='Test', description='Testdescription')
    except falcon.HTTPPreconditionRequired as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_too_many_requests_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPTooManyRequests()
    except falcon.HTTPTooManyRequests as e:
        assert status.HTTP_429 == e.title
        assert e.description is None
        assert 'Retry-After' not in e.headers


def test_http_too_many_requests_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPTooManyRequests(
            title='Test',
            description='Testdescription',
            retry_after=123
        )
    except falcon.HTTPTooManyRequests as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description
        assert '123' == e.headers['Retry-After']


def test_http_request_header_fields_too_large_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPRequestHeaderFieldsTooLarge()
    except falcon.HTTPRequestHeaderFieldsTooLarge as e:
        assert status.HTTP_431 == e.title
        assert e.description is None


def test_http_request_header_fields_too_large_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPRequestHeaderFieldsTooLarge(
            title='Test',
            description='Testdescription'
        )
    except falcon.HTTPRequestHeaderFieldsTooLarge as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_unavailable_for_legal_reasons_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPUnavailableForLegalReasons()
    except falcon.HTTPUnavailableForLegalReasons as e:
        assert status.HTTP_451 == e.title
        assert e.description is None


def test_http_unavailable_for_legal_reasons_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPUnavailableForLegalReasons(
            title='Test',
            description='Testdescription'
        )
    except falcon.HTTPUnavailableForLegalReasons as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_internal_server_error_entity_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPInternalServerError()
    except falcon.HTTPInternalServerError as e:
        assert status.HTTP_500 == e.title
        assert e.description is None


def test_http_internal_server_error_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPInternalServerError(title='Test', description='Testdescription')
    except falcon.HTTPInternalServerError as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_bad_gateway_entity_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPBadGateway()
    except falcon.HTTPBadGateway as e:
        assert status.HTTP_502 == e.title
        assert e.description is None


def test_http_bad_gateway_entity_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPBadGateway(title='Test', description='Testdescription')
    except falcon.HTTPBadGateway as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_service_unavailable_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPServiceUnavailable()
    except falcon.HTTPServiceUnavailable as e:
        assert status.HTTP_503 == e.title
        assert e.description is None
        assert 'Retry-After' not in e.headers


def test_http_service_unavailable_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPServiceUnavailable(
            title='Test',
            description='Testdescription',
            retry_after=123
        )
    except falcon.HTTPServiceUnavailable as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description
        assert e.headers['Retry-After'] == '123'


def test_http_insufficient_storage_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPInsufficientStorage()
    except falcon.HTTPInsufficientStorage as e:
        assert status.HTTP_507 == e.title
        assert e.description is None


def test_http_insufficient_storage_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPInsufficientStorage(title='Test', description='Testdescription')
    except falcon.HTTPInsufficientStorage as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_loop_detected_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPLoopDetected()
    except falcon.HTTPLoopDetected as e:
        assert status.HTTP_508 == e.title
        assert e.description is None


def test_http_loop_detected_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPLoopDetected(title='Test', description='Testdescription')
    except falcon.HTTPLoopDetected as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_network_authentication_required_no_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPNetworkAuthenticationRequired()
    except falcon.HTTPNetworkAuthenticationRequired as e:
        assert status.HTTP_511 == e.title
        assert e.description is None


def test_http_network_authentication_required_with_title_and_desc_and_challenges():
    try:
        raise falcon.HTTPNetworkAuthenticationRequired(
            title='Test',
            description='Testdescription'
        )
    except falcon.HTTPNetworkAuthenticationRequired as e:
        assert 'Test' == e.title
        assert 'Testdescription' == e.description


def test_http_error_repr():
    error = falcon.HTTPBadRequest()
    _repr = '<%s: %s>' % (error.__class__.__name__, error.status)
    assert error.__repr__() == _repr
