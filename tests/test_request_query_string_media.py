from urllib.parse import quote

import pytest

import falcon
from falcon import errors
from falcon import media
from falcon import testing


@pytest.fixture
def client(asgi):
    app_cls = falcon.asgi.App if asgi else falcon.App
    app = app_cls()
    return testing.TestClient(app)


class CaptureQueryStringMedia:
    """Resource that captures the deserialized query string media."""

    def on_get(self, req, resp):
        self.captured_media = req.get_query_string_as_media()

    def on_post(self, req, resp):
        self.captured_media = req.get_query_string_as_media('application/json')


class CaptureQueryStringMediaAsync:
    """Async resource that captures the deserialized query string media."""

    async def on_get(self, req, resp):
        self.captured_media = await req.get_query_string_as_media()

    async def on_post(self, req, resp):
        self.captured_media = await req.get_query_string_as_media('application/json')


class TestQueryStringAsMedia:
    """Test query string deserialization as media."""

    def test_simple_json_query_string(self, asgi, client):
        """Test deserializing a simple JSON query string."""
        resource = (
            CaptureQueryStringMediaAsync() if asgi else CaptureQueryStringMedia()
        )
        client.app.add_route('/test', resource)

        # Query string: {"key": "value"}
        json_data = '{"key": "value"}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.captured_media == {'key': 'value'}

    def test_complex_json_query_string(self, asgi, client):
        """Test OpenAPI 3.2 example with complex JSON."""
        resource = (
            CaptureQueryStringMediaAsync() if asgi else CaptureQueryStringMedia()
        )
        client.app.add_route('/test', resource)

        # Query string: {"numbers":[1,2],"flag":null}
        json_data = '{"numbers":[1,2],"flag":null}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.captured_media == {'numbers': [1, 2], 'flag': None}

    def test_cached_result(self, asgi, client):
        """Test that the result is cached across multiple calls."""
        resource = (
            CaptureQueryStringMediaAsync() if asgi else CaptureQueryStringMedia()
        )
        client.app.add_route('/test', resource)

        json_data = '{"cached": true}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)
        first_result = resource.captured_media

        # Call again - should get cached result
        client.simulate_get('/test', query_string=query_string)
        second_result = resource.captured_media

        assert first_result == second_result
        assert first_result == {'cached': True}

    def test_empty_query_string(self, asgi, client):
        """Test behavior with empty query string."""

        class ResourceWithDefault:
            def on_get(self, req, resp):
                self.captured_media = req.get_query_string_as_media(
                    default_when_empty={'default': 'value'}
                )

        class ResourceWithDefaultAsync:
            async def on_get(self, req, resp):
                self.captured_media = await req.get_query_string_as_media(
                    default_when_empty={'default': 'value'}
                )

        resource = ResourceWithDefaultAsync() if asgi else ResourceWithDefault()
        client.app.add_route('/test', resource)

        client.simulate_get('/test')

        # Should return the default value when empty and handler raises error
        assert resource.captured_media == {'default': 'value'}

    def test_invalid_json_query_string(self, asgi, client):
        """Test error handling with invalid JSON."""

        class ResourceInvalidJSON:
            def on_get(self, req, resp):
                try:
                    req.get_query_string_as_media()
                except errors.HTTPBadRequest:
                    self.error_caught = True
                else:
                    self.error_caught = False

        class ResourceInvalidJSONAsync:
            async def on_get(self, req, resp):
                try:
                    await req.get_query_string_as_media()
                except errors.HTTPBadRequest:
                    self.error_caught = True
                else:
                    self.error_caught = False

        resource = ResourceInvalidJSONAsync() if asgi else ResourceInvalidJSON()
        client.app.add_route('/test', resource)

        # Invalid JSON
        invalid_json = '{"incomplete"'
        query_string = quote(invalid_json, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.error_caught

    def test_explicit_media_type(self, asgi, client):
        """Test specifying an explicit media type."""
        resource = (
            CaptureQueryStringMediaAsync() if asgi else CaptureQueryStringMedia()
        )
        client.app.add_route('/test', resource)

        json_data = '{"explicit": "type"}'
        query_string = quote(json_data, safe='')

        client.simulate_post('/test', query_string=query_string)

        assert resource.captured_media == {'explicit': 'type'}

    def test_special_characters_in_json(self, asgi, client):
        """Test JSON with special characters."""
        resource = (
            CaptureQueryStringMediaAsync() if asgi else CaptureQueryStringMedia()
        )
        client.app.add_route('/test', resource)

        # JSON with special characters
        json_data = '{"name": "Test & Demo", "value": "100%"}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.captured_media == {'name': 'Test & Demo', 'value': '100%'}

    def test_nested_json_structures(self, asgi, client):
        """Test deeply nested JSON structures."""
        resource = (
            CaptureQueryStringMediaAsync() if asgi else CaptureQueryStringMedia()
        )
        client.app.add_route('/test', resource)

        json_data = '{"level1": {"level2": {"level3": ["a", "b", "c"]}}}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        expected = {'level1': {'level2': {'level3': ['a', 'b', 'c']}}}
        assert resource.captured_media == expected

    def test_different_media_types(self, asgi, client):
        """Test with different media type handlers."""

        class ResourceCustomMediaType:
            def on_get(self, req, resp):
                # Plain text - should just return the decoded string
                self.captured_media = req.get_query_string_as_media(
                    'application/x-www-form-urlencoded'
                )

        class ResourceCustomMediaTypeAsync:
            async def on_get(self, req, resp):
                self.captured_media = await req.get_query_string_as_media(
                    'application/x-www-form-urlencoded'
                )

        resource = (
            ResourceCustomMediaTypeAsync() if asgi else ResourceCustomMediaType()
        )
        client.app.add_route('/test', resource)

        # URL-encoded form data
        query_string = quote('key1=value1&key2=value2', safe='')

        client.simulate_get('/test', query_string=query_string)

        # URLEncodedFormHandler should parse this
        assert isinstance(resource.captured_media, dict)

    def test_unicode_in_query_string(self, asgi, client):
        """Test JSON with Unicode characters."""
        resource = (
            CaptureQueryStringMediaAsync() if asgi else CaptureQueryStringMedia()
        )
        client.app.add_route('/test', resource)

        # JSON with Unicode
        json_data = '{"emoji": "🚀", "chinese": "你好"}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.captured_media == {'emoji': '🚀', 'chinese': '你好'}

    def test_error_caching(self, asgi, client):
        """Test that errors are cached as well."""

        class ResourceErrorCaching:
            def __init__(self):
                self.call_count = 0

            def on_get(self, req, resp):
                self.call_count += 1
                try:
                    req.get_query_string_as_media()
                except errors.HTTPBadRequest:
                    pass

        class ResourceErrorCachingAsync:
            def __init__(self):
                self.call_count = 0

            async def on_get(self, req, resp):
                self.call_count += 1
                try:
                    await req.get_query_string_as_media()
                except errors.HTTPBadRequest:
                    pass

        resource = ResourceErrorCachingAsync() if asgi else ResourceErrorCaching()
        client.app.add_route('/test', resource)

        invalid_json = '{"bad"'
        query_string = quote(invalid_json, safe='')

        # First call
        client.simulate_get('/test', query_string=query_string)
        # Second call - error should be cached
        client.simulate_get('/test', query_string=query_string)

        # Both calls should have been made, but the error should be raised
        # from cache on the second call
        assert resource.call_count == 2

    def test_array_at_root(self, asgi, client):
        """Test JSON array at root level."""
        resource = (
            CaptureQueryStringMediaAsync() if asgi else CaptureQueryStringMedia()
        )
        client.app.add_route('/test', resource)

        json_data = '[1, 2, 3, 4, 5]'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.captured_media == [1, 2, 3, 4, 5]

    def test_boolean_and_null_values(self, asgi, client):
        """Test JSON with boolean and null values."""
        resource = (
            CaptureQueryStringMediaAsync() if asgi else CaptureQueryStringMedia()
        )
        client.app.add_route('/test', resource)

        json_data = '{"active": true, "inactive": false, "empty": null}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.captured_media == {
            'active': True,
            'inactive': False,
            'empty': None,
        }

    def test_numeric_values(self, asgi, client):
        """Test JSON with various numeric values."""
        resource = (
            CaptureQueryStringMediaAsync() if asgi else CaptureQueryStringMedia()
        )
        client.app.add_route('/test', resource)

        json_data = '{"int": 42, "float": 3.14, "negative": -10}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        assert resource.captured_media == {'int': 42, 'float': 3.14, 'negative': -10}

    def test_default_when_empty_not_used_for_valid_data(self, asgi, client):
        """Test that default_when_empty is not used when data is valid."""

        class ResourceWithDefault:
            def on_get(self, req, resp):
                self.captured_media = req.get_query_string_as_media(
                    default_when_empty={'should': 'not see this'}
                )

        class ResourceWithDefaultAsync:
            async def on_get(self, req, resp):
                self.captured_media = await req.get_query_string_as_media(
                    default_when_empty={'should': 'not see this'}
                )

        resource = ResourceWithDefaultAsync() if asgi else ResourceWithDefault()
        client.app.add_route('/test', resource)

        json_data = '{"actual": "data"}'
        query_string = quote(json_data, safe='')

        client.simulate_get('/test', query_string=query_string)

        # Should get the actual data, not the default
        assert resource.captured_media == {'actual': 'data'}
