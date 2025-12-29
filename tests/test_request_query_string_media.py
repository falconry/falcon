from urllib.parse import quote

import falcon
from falcon import errors
from falcon import testing


class CaptureQueryStringMedia:
    """Resource that captures the deserialized query string media."""

    def on_get(self, req, resp):
        self.captured_media = req.get_query_string_as_media()

    def on_post(self, req, resp):
        self.captured_media = req.get_query_string_as_media('application/json')


class TestQueryStringAsMedia:
    """Test query string deserialization as media."""

    def test_simple_json_query_string(self, asgi, util):
        """Test deserializing a simple JSON query string."""
        resource = CaptureQueryStringMedia()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        # Query string: {"key": "value"}
        json_data = '{"key": "value"}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.captured_media == {'key': 'value'}

    def test_complex_json_query_string(self, asgi, util):
        """Test OpenAPI 3.2 example with complex JSON."""
        resource = CaptureQueryStringMedia()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        # Query string: {"numbers":[1,2],"flag":null}
        json_data = '{"numbers":[1,2],"flag":null}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.captured_media == {'numbers': [1, 2], 'flag': None}

    def test_empty_query_string(self, asgi, util):
        """Test behavior with empty query string."""

        class ResourceWithDefault:
            def on_get(self, req, resp):
                self.captured_media = req.get_query_string_as_media(
                    default_when_empty={'default': 'value'}
                )

        resource = ResourceWithDefault()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        client.simulate_get('/test')

        # Should return the default value when empty and handler raises error
        assert resource.captured_media == {'default': 'value'}

    def test_invalid_json_query_string(self, asgi, util):
        """Test error handling with invalid JSON."""

        class ResourceInvalidJSON:
            def on_get(self, req, resp):
                try:
                    req.get_query_string_as_media()
                except errors.HTTPBadRequest:
                    self.error_caught = True
                else:
                    self.error_caught = False

        resource = ResourceInvalidJSON()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        # Invalid JSON
        invalid_json = '{"incomplete"'
        query_string = quote(invalid_json, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.error_caught

    def test_explicit_media_type(self, asgi, util):
        """Test specifying an explicit media type."""
        resource = CaptureQueryStringMedia()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        json_data = '{"explicit": "type"}'
        query_string = quote(json_data, safe='')

        client.simulate_post('/test', query_string=query_string)

        assert resource.captured_media == {'explicit': 'type'}

    def test_special_characters_in_json(self, asgi, util):
        """Test JSON with special characters."""
        resource = CaptureQueryStringMedia()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        # JSON with special characters
        json_data = '{"name": "Test & Demo", "value": "100%"}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.captured_media == {'name': 'Test & Demo', 'value': '100%'}

    def test_nested_json_structures(self, asgi, util):
        """Test deeply nested JSON structures."""
        resource = CaptureQueryStringMedia()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        json_data = '{"level1": {"level2": {"level3": ["a", "b", "c"]}}}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        expected = {'level1': {'level2': {'level3': ['a', 'b', 'c']}}}
        assert resource.captured_media == expected

    def test_different_media_types(self, asgi, util):
        """Test with different media type handlers."""

        class ResourceCustomMediaType:
            def on_get(self, req, resp):
                # Plain text - should just return the decoded string
                self.captured_media = req.get_query_string_as_media(
                    'application/x-www-form-urlencoded'
                )

        resource = ResourceCustomMediaType()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        # URL-encoded form data
        query_string = quote('key1=value1&key2=value2', safe='')

        client.simulate_get('/test', query_string=query_string)

        # URLEncodedFormHandler should parse this
        assert isinstance(resource.captured_media, dict)

    def test_unicode_in_query_string(self, asgi, util):
        """Test JSON with Unicode characters."""
        resource = CaptureQueryStringMedia()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        # JSON with Unicode
        json_data = '{"emoji": "🚀", "chinese": "你好"}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.captured_media == {'emoji': '🚀', 'chinese': '你好'}

    def test_error_caching(self, asgi, util):
        """Test error behavior on repeated calls."""

        class ResourceErrorCaching:
            def __init__(self):
                self.call_count = 0

            def on_get(self, req, resp):
                self.call_count += 1
                try:
                    req.get_query_string_as_media()
                except errors.HTTPBadRequest:
                    pass

        resource = ResourceErrorCaching()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        invalid_json = '{"bad"'
        query_string = quote(invalid_json, safe='')

        # First call
        client.simulate_get('/test', query_string=query_string)
        # Second call
        client.simulate_get('/test', query_string=query_string)

        # Both calls should have been made
        assert resource.call_count == 2

    def test_array_at_root(self, asgi, util):
        """Test JSON array at root level."""
        resource = CaptureQueryStringMedia()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        json_data = '[1, 2, 3, 4, 5]'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.captured_media == [1, 2, 3, 4, 5]

    def test_boolean_and_null_values(self, asgi, util):
        """Test JSON with boolean and null values."""
        resource = CaptureQueryStringMedia()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        json_data = '{"active": true, "inactive": false, "empty": null}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.captured_media == {
            'active': True,
            'inactive': False,
            'empty': None,
        }

    def test_numeric_values(self, asgi, util):
        """Test JSON with various numeric values."""
        resource = CaptureQueryStringMedia()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        json_data = '{"int": 42, "float": 3.14, "negative": -10}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.captured_media == {'int': 42, 'float': 3.14, 'negative': -10}

    def test_default_when_empty_not_used_for_valid_data(self, asgi, util):
        """Test that default_when_empty is not used when data is valid."""

        class ResourceWithDefault:
            def on_get(self, req, resp):
                self.captured_media = req.get_query_string_as_media(
                    default_when_empty={'should': 'not see this'}
                )

        resource = ResourceWithDefault()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        json_data = '{"actual": "data"}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        # Should get the actual data, not the default
        assert resource.captured_media == {'actual': 'data'}

    def test_error_propagation(self, asgi, util):
        """Test that non-MediaNotFoundError exceptions propagate correctly."""

        class FailingHandler:
            exhaust_stream = False

            def deserialize(self, stream, content_type, content_length):
                raise ValueError('Custom error')

        class ResourceErrorCheck:
            def on_get(self, req, resp):
                try:
                    req.get_query_string_as_media('application/custom')
                except ValueError as e:
                    self.error_message = str(e)

        resource = ResourceErrorCheck()
        handler = FailingHandler()

        app = util.create_app(asgi)
        app.req_options.media_handlers['application/custom'] = handler
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        client.simulate_get('/test', query_string='data')

        assert resource.error_message == 'Custom error'

    def test_uses_default_media_type_when_none_specified(self, asgi, util):
        """Test that default media type is used when media_type is None."""

        class ResourceDefaultType:
            def on_get(self, req, resp):
                # Don't specify media_type, should use default (application/json)
                self.captured_media = req.get_query_string_as_media()

        resource = ResourceDefaultType()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        json_data = '{"uses": "default"}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.captured_media == {'uses': 'default'}

    def test_cached_error_with_default_when_empty(self, asgi, util):
        """Test that an error followed by default_when_empty returns default."""

        class ResourceCachedError:
            def on_get(self, req, resp):
                # First call - will fail
                try:
                    req.get_query_string_as_media()
                except Exception:
                    pass
                # Second call - should return default
                self.result = req.get_query_string_as_media(default_when_empty={})

        resource = ResourceCachedError()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        # Empty query string will cause MediaNotFoundError
        client.simulate_get('/test', query_string='')

        assert resource.result == {}

    def test_cached_error_reraises_without_default(self, asgi, util):
        """Test that error is re-raised on subsequent calls."""

        class ResourceCachedErrorReraise:
            def on_get(self, req, resp):
                # First call - will fail
                try:
                    req.get_query_string_as_media()
                except falcon.MediaNotFoundError:
                    pass
                # Second call - should re-raise error
                try:
                    req.get_query_string_as_media()
                except falcon.MediaNotFoundError as err:
                    self.error_caught = str(err)

        resource = ResourceCachedErrorReraise()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        client.simulate_get('/test', query_string='')

        assert 'MediaNotFoundError' in resource.error_caught

    def test_unsupported_media_type_raises_value_error(self, asgi, util):
        """Test unsupported media type raises ValueError."""

        class ResourceUnsupportedMedia:
            def on_get(self, req, resp):
                try:
                    # Request a media type that doesn't exist
                    req.get_query_string_as_media('application/x-nonexistent')
                except ValueError as e:
                    self.error_caught = True
                    self.error_message = str(e)
                except Exception:
                    self.error_caught = False

        resource = ResourceUnsupportedMedia()
        app = util.create_app(asgi)
        app.add_route('/test', resource)
        client = testing.TestClient(app)

        json_data = '{"test": "data"}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.error_caught
        assert 'No media handler is configured' in resource.error_message
        assert 'application/x-nonexistent' in resource.error_message
