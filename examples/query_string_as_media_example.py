import falcon


class QueryStringMediaResource:
    """Resource that accepts JSON data in the query string."""

    def on_get(self, req, resp):
        """Handle GET requests with JSON in the query string.

        Example URLs:
            # Simple JSON object
            GET /search?%7B%22term%22%3A%22falcon%22%7D
            # Decoded: {"term":"falcon"}

            # Complex JSON with arrays
            GET /filter?%7B%22numbers%22%3A%5B1%2C2%2C3%5D%2C%22flag%22%3Anull%7D
            # Decoded: {"numbers":[1,2,3],"flag":null}
        """
        try:
            # Deserialize the entire query string as JSON
            data = req.get_query_string_as_media('application/json')

            # Process the data
            resp.media = {
                'message': 'Query string successfully deserialized',
                'received_data': data,
            }
            resp.status = falcon.HTTP_200

        except falcon.HTTPBadRequest as e:
            # Handle invalid JSON in query string
            resp.media = {
                'error': 'Invalid JSON in query string',
                'details': e.description,
            }
            resp.status = falcon.HTTP_400

    def on_post(self, req, resp):
        """Handle POST requests with optional query string media.

        This demonstrates that you can use both request body media
        and query string media in the same request.
        """
        # Get data from request body
        body_data = req.get_media()

        # Optionally get filter parameters from query string
        filter_params = None
        if req.query_string:
            try:
                filter_params = req.get_query_string_as_media('application/json')
            except falcon.HTTPBadRequest:
                # Query string is optional, ignore if invalid
                pass

        resp.media = {
            'body_data': body_data,
            'filter_params': filter_params,
        }
        resp.status = falcon.HTTP_200


class DefaultWhenEmptyResource:
    """Resource demonstrating the default_when_empty parameter."""

    def on_get(self, req, resp):
        """Handle GET requests with optional query string media.

        If no query string is provided, returns a default value.
        """
        # Use default value when query string is empty
        data = req.get_query_string_as_media(
            'application/json', default_when_empty={'default': 'no query provided'}
        )

        resp.media = {'data': data}
        resp.status = falcon.HTTP_200


# Create the Falcon application
app = falcon.App()

# Add routes
app.add_route('/search', QueryStringMediaResource())
app.add_route('/filter', QueryStringMediaResource())
app.add_route('/optional', DefaultWhenEmptyResource())


if __name__ == '__main__':
    from wsgiref.simple_server import make_server

    print('Starting server on http://localhost:8000')
    print('\nTry these example requests:')
    print('  Simple JSON:')
    print('    curl "http://localhost:8000/search?%7B%22term%22%3A%22falcon%22%7D"')
    print('\n  Complex JSON:')
    print(
        '    curl "http://localhost:8000/filter?%7B%22numbers%22%3A%5B1%2C2%2C3%5D%7D"'
    )
    print('\n  Optional query string:')
    print('    curl "http://localhost:8000/optional"')
    print('    curl "http://localhost:8000/optional?%7B%22test%22%3Atrue%7D"')
    print()

    with make_server('', 8000, app) as httpd:
        httpd.serve_forever()
