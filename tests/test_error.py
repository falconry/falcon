import testtools
import falcon
import falcon.status_codes as status


class TestError(testtools.TestCase):
    def test_http_bad_request_no_title_and_desc(self):
        try:
            raise falcon.HTTPBadRequest()
        except falcon.HTTPBadRequest as e:
            self.assertEqual(status.HTTP_400, e.title,
                             'The title should be ' + status.HTTP_400 + ', but it is: ' + e.title)
            self.assertEqual(None, e.description, 'The description should be None')

    def test_http_bad_request_with_title_and_desc(self):
        try:
            raise falcon.HTTPBadRequest(title='Test', description='Testdescription')
        except falcon.HTTPBadRequest as e:
            self.assertEqual('Test', e.title, 'Title should be "Test"')
            self.assertEqual('Testdescription', e.description,
                             'Description should be "Testdescription"')

    def test_http_unauthorized_no_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPUnauthorized()
        except falcon.HTTPUnauthorized as e:
            self.assertEqual(status.HTTP_401, e.title,
                             'The title should be ' + status.HTTP_401 + ', but it is: ' + e.title)
            self.assertEqual(None, e.description, 'The description should be None')
            self.assertNotIn('WWW-Authenticate', e.headers,
                             'Challenges should not be found in headers')

    def test_http_unauthorized_with_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPUnauthorized(title='Test', description='Testdescription',
                                          challenges=['Testch'])
        except falcon.HTTPUnauthorized as e:
            self.assertEqual('Test', e.title, 'Title should be "Test"')
            self.assertEqual('Testdescription', e.description,
                             'Description should be "Testdescription"')
            self.assertEqual('Testch', e.headers['WWW-Authenticate'], 'Challenges should be None')

    def test_http_forbidden_no_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPForbidden()
        except falcon.HTTPForbidden as e:
            self.assertEqual(status.HTTP_403, e.title,
                             'The title should be ' + status.HTTP_403 + ', but it is: ' + e.title)
            self.assertEqual(None, e.description, 'The description should be None')

    def test_http_forbidden_with_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPForbidden(title='Test', description='Testdescription')
        except falcon.HTTPForbidden as e:
            self.assertEqual('Test', e.title, 'Title should be "Test"')
            self.assertEqual('Testdescription', e.description,
                             'Description should be "Testdescription"')

    def test_http_not_acceptable_no_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPNotAcceptable()
        except falcon.HTTPNotAcceptable as e:
            self.assertEqual(None, e.description, 'The description should be None')

    def test_http_not_acceptable_with_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPNotAcceptable(description='Testdescription')
        except falcon.HTTPNotAcceptable as e:
            self.assertEqual('Testdescription', e.description,
                             'Description should be "Testdescription"')

    def test_http_conflict_no_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPConflict()
        except falcon.HTTPConflict as e:
            self.assertEqual(status.HTTP_409, e.title,
                             'The title should be ' + status.HTTP_409 + ', but it is: ' + e.title)
            self.assertEqual(None, e.description, 'The description should be None')

    def test_http_conflict_with_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPConflict(title='Test', description='Testdescription')
        except falcon.HTTPConflict as e:
            self.assertEqual('Test', e.title, 'Title should be "Test"')
            self.assertEqual('Testdescription', e.description,
                             'Description should be "Testdescription"')

    def test_http_length_required_no_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPLengthRequired()
        except falcon.HTTPLengthRequired as e:
            self.assertEqual(status.HTTP_411, e.title,
                             'The title should be ' + status.HTTP_411 + ', but it is: ' + e.title)
            self.assertEqual(None, e.description, 'The description should be None')

    def test_http_length_required_with_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPLengthRequired(title='Test', description='Testdescription')
        except falcon.HTTPLengthRequired as e:
            self.assertEqual('Test', e.title, 'Title should be "Test"')
            self.assertEqual('Testdescription', e.description,
                             'Description should be "Testdescription"')

    def test_http_precondition_failed_no_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPPreconditionFailed()
        except falcon.HTTPPreconditionFailed as e:
            self.assertEqual(status.HTTP_412, e.title,
                             'The title should be ' + status.HTTP_412 + ', but it is: ' + e.title)
            self.assertEqual(None, e.description, 'The description should be None')

    def test_http_precondition_faild_with_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPPreconditionFailed(title='Test', description='Testdescription')
        except falcon.HTTPPreconditionFailed as e:
            self.assertEqual('Test', e.title, 'Title should be "Test"')
            self.assertEqual('Testdescription', e.description,
                             'Description should be "Testdescription"')

    def test_http_request_entity_too_large_no_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPRequestEntityTooLarge()
        except falcon.HTTPRequestEntityTooLarge as e:
            self.assertEqual(status.HTTP_413, e.title,
                             'The title should be ' + status.HTTP_413 + ', but it is: ' + e.title)
            self.assertEqual(None, e.description, 'The description should be None')
            self.assertNotIn('Retry-After', e.headers, 'Retry-After should not be in the headers')

    def test_http_request_entity_too_large_with_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPRequestEntityTooLarge(title='Test', description='Testdescription',
                                                   retry_after=123)
        except falcon.HTTPRequestEntityTooLarge as e:
            self.assertEqual('Test', e.title, 'Title should be "Test"')
            self.assertEqual('Testdescription', e.description,
                             'Description should be "Testdescription"')
            self.assertEqual('123', e.headers['Retry-After'], 'Retry-After should be 123')

    def test_http_uri_too_long_no_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPUriTooLong()
        except falcon.HTTPUriTooLong as e:
            self.assertEqual(status.HTTP_414, e.title,
                             'The title should be ' + status.HTTP_414 + ', but it is: ' + e.title)
            self.assertEqual(None, e.description, 'The description should be None')

    def test_http_uri_too_long_with_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPUriTooLong(title='Test', description='Testdescription')
        except falcon.HTTPUriTooLong as e:
            self.assertEqual('Test', e.title, 'Title should be "Test"')
            self.assertEqual('Testdescription', e.description,
                             'Description should be "Testdescription"')

    def test_http_unsupported_media_type_no_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPUnsupportedMediaType()
        except falcon.HTTPUnsupportedMediaType as e:
            self.assertEqual(None, e.description, 'The description should be None')

    def test_http_unsupported_media_type_with_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPUnsupportedMediaType(description='Testdescription')
        except falcon.HTTPUnsupportedMediaType as e:
            self.assertEqual('Testdescription', e.description,
                             'Description should be "Testdescription"')

    def test_http_unprocessable_entity_no_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPUnprocessableEntity()
        except falcon.HTTPUnprocessableEntity as e:
            self.assertEqual(status.HTTP_422, e.title,
                             'The title should be ' + status.HTTP_422 + ', but it is: ' + e.title)
            self.assertEqual(None, e.description, 'The description should be None')

    def test_http_unprocessable_with_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPUnprocessableEntity(title='Test', description='Testdescription')
        except falcon.HTTPUnprocessableEntity as e:
            self.assertEqual('Test', e.title, 'Title should be "Test"')
            self.assertEqual('Testdescription', e.description,
                             'Description should be "Testdescription"')

    def test_http_too_many_requests_no_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPTooManyRequests()
        except falcon.HTTPTooManyRequests as e:
            self.assertEqual(status.HTTP_429, e.title,
                             'The title should be ' + status.HTTP_429 + ', but it is: ' + e.title)
            self.assertEqual(None, e.description, 'The description should be None')
            self.assertNotIn('Retry-After', e.headers, 'Retry-After should not be in the headers')

    def test_http_too_many_requests_with_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPTooManyRequests(title='Test', description='Testdescription',
                                             retry_after=123)
        except falcon.HTTPTooManyRequests as e:
            self.assertEqual('Test', e.title, 'Title should be "Test"')
            self.assertEqual('Testdescription', e.description,
                             'Description should be "Testdescription"')
            self.assertEqual('123', e.headers['Retry-After'], 'Retry-After should be 123')

    def test_http_unavailable_for_legal_reasons_no_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPUnavailableForLegalReasons()
        except falcon.HTTPUnavailableForLegalReasons as e:
            self.assertEqual(status.HTTP_451, e.title,
                             'The title should be ' + status.HTTP_451 + ', but it is: ' + e.title)
            self.assertEqual(None, e.description, 'The description should be None')

    def test_http_unavailable_for_legal_reasons_with_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPUnavailableForLegalReasons(title='Test',
                                                        description='Testdescription')
        except falcon.HTTPUnavailableForLegalReasons as e:
            self.assertEqual('Test', e.title, 'Title should be "Test"')
            self.assertEqual('Testdescription', e.description,
                             'Description should be "Testdescription"')

    def test_http_internal_server_error_entity_no_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPInternalServerError()
        except falcon.HTTPInternalServerError as e:
            self.assertEqual(status.HTTP_500, e.title,
                             'The title should be ' + status.HTTP_500 + ', but it is: ' + e.title)
            self.assertEqual(None, e.description, 'The description should be None')

    def test_http_internal_server_error_with_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPInternalServerError(title='Test', description='Testdescription')
        except falcon.HTTPInternalServerError as e:
            self.assertEqual('Test', e.title, 'Title should be "Test"')
            self.assertEqual('Testdescription', e.description,
                             'Description should be "Testdescription"')

    def test_http_bad_gateway_entity_no_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPBadGateway()
        except falcon.HTTPBadGateway as e:
            self.assertEqual(status.HTTP_502, e.title,
                             'The title should be ' + status.HTTP_502 + ', but it is: ' + e.title)
            self.assertEqual(None, e.description, 'The description should be None')

    def test_http_bad_gateway_entity_with_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPBadGateway(title='Test', description='Testdescription')
        except falcon.HTTPBadGateway as e:
            self.assertEqual('Test', e.title, 'Title should be "Test"')
            self.assertEqual('Testdescription', e.description,
                             'Description should be "Testdescription"')

    def test_http_service_unavailable_no_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPServiceUnavailable()
        except falcon.HTTPServiceUnavailable as e:
            self.assertEqual(status.HTTP_503, e.title,
                             'The title should be ' + status.HTTP_503 + ', but it is: ' + e.title)
            self.assertEqual(None, e.description, 'The description should be None')
            self.assertNotIn('Retry-After', e.headers, 'Retry-After should not be in the headers')

    def test_http_service_unavailable_with_title_and_desc_and_challenges(self):
        try:
            raise falcon.HTTPServiceUnavailable(title='Test', description='Testdescription',
                                                retry_after=123)
        except falcon.HTTPServiceUnavailable as e:
            self.assertEqual('Test', e.title, 'Title should be "Test"')
            self.assertEqual('Testdescription', e.description,
                             'Description should be "Testdescription"')
            self.assertEqual('123', e.headers['Retry-After'], 'Retry-After should be 123')
