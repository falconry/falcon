"""Smoke tests verifying basic functionality without any 3rd party deps.

These tests use only the Python standard library's ``unittest`` framework
and Falcon's own ``falcon.testing`` helpers (which themselves only depend on
the standard library when ``testtools`` is not installed).

They are intentionally minimal: the goal is a fast import-and-route
sanity check that can be run against a fresh ``pip install falcon`` with
no additional packages.
"""

import json
import unittest

import falcon
import falcon.asgi
import falcon.testing

# ---------------------------------------------------------------------------
# Shared resources
# ---------------------------------------------------------------------------


class _HelloResource:
    """Simple WSGI responder returning JSON and plain text."""

    def on_get(self, req: falcon.Request, resp: falcon.Response) -> None:
        """Handle GET: return JSON greeting."""
        resp.media = {'message': 'Hello, World!', 'path': req.path}

    def on_post(self, req: falcon.Request, resp: falcon.Response) -> None:
        """Handle POST: echo the request body as plain text."""
        resp.content_type = falcon.MEDIA_TEXT
        resp.text = req.bounded_stream.read().decode()
        resp.status = falcon.HTTP_201


class _HelloAsgiResource:
    """Simple ASGI responder returning JSON and plain text."""

    async def on_get(
        self, req: falcon.asgi.Request, resp: falcon.asgi.Response
    ) -> None:
        """Handle GET: return JSON greeting."""
        resp.media = {'message': 'Hello, World!', 'path': req.path}

    async def on_post(
        self, req: falcon.asgi.Request, resp: falcon.asgi.Response
    ) -> None:
        """Handle POST: echo the request body as plain text."""
        resp.content_type = falcon.MEDIA_TEXT
        resp.text = (await req.bounded_stream.read()).decode()
        resp.status = falcon.HTTP_201


# ---------------------------------------------------------------------------
# WSGI smoke tests
# ---------------------------------------------------------------------------


class TestWSGISmoke(unittest.TestCase):
    """Basic WSGI smoke tests that require no third-party packages."""

    def setUp(self) -> None:
        """Set up a minimal WSGI app and test client."""
        self.app = falcon.App()
        self.app.add_route('/hello', _HelloResource())
        self.client = falcon.testing.TestClient(self.app)

    def test_app_instantiation(self) -> None:
        """falcon.App() must be callable immediately after construction."""
        self.assertTrue(callable(self.app))

    def test_get_returns_200(self) -> None:
        """GET /hello must return HTTP 200 with a JSON body."""
        result = self.client.simulate_get('/hello')
        self.assertEqual(result.status_code, 200)

    def test_get_json_body(self) -> None:
        """GET /hello must return a valid JSON response with expected keys."""
        result = self.client.simulate_get('/hello')
        body = json.loads(result.text)
        self.assertEqual(body['message'], 'Hello, World!')
        self.assertEqual(body['path'], '/hello')

    def test_get_content_type_json(self) -> None:
        """GET /hello must return application/json by default."""
        result = self.client.simulate_get('/hello')
        self.assertIn('application/json', result.headers.get('content-type', ''))

    def test_post_returns_201(self) -> None:
        """POST /hello must return HTTP 201."""
        result = self.client.simulate_post('/hello', body='ping')
        self.assertEqual(result.status_code, 201)

    def test_post_echoes_body(self) -> None:
        """POST /hello must echo the request body back as plain text."""
        result = self.client.simulate_post('/hello', body='ping')
        self.assertEqual(result.text, 'ping')

    def test_404_on_unknown_route(self) -> None:
        """An unmapped path must return HTTP 404."""
        result = self.client.simulate_get('/no-such-route')
        self.assertEqual(result.status_code, 404)

    def test_405_on_disallowed_method(self) -> None:
        """A mapped path must return HTTP 405 for an unsupported method."""
        result = self.client.simulate_delete('/hello')
        self.assertEqual(result.status_code, 405)


# ---------------------------------------------------------------------------
# ASGI smoke tests
# ---------------------------------------------------------------------------


class TestASGISmoke(unittest.TestCase):
    """Basic ASGI smoke tests that require no third-party packages."""

    def setUp(self) -> None:
        """Set up a minimal ASGI app and test client."""
        self.app = falcon.asgi.App()
        self.app.add_route('/hello', _HelloAsgiResource())
        self.client = falcon.testing.TestClient(self.app)

    def test_app_instantiation(self) -> None:
        """falcon.asgi.App() must be callable immediately after construction."""
        self.assertTrue(callable(self.app))

    def test_get_returns_200(self) -> None:
        """GET /hello must return HTTP 200 with a JSON body (ASGI)."""
        result = self.client.simulate_get('/hello')
        self.assertEqual(result.status_code, 200)

    def test_get_json_body(self) -> None:
        """GET /hello must return valid JSON with expected keys (ASGI)."""
        result = self.client.simulate_get('/hello')
        body = json.loads(result.text)
        self.assertEqual(body['message'], 'Hello, World!')
        self.assertEqual(body['path'], '/hello')

    def test_get_content_type_json(self) -> None:
        """GET /hello must return application/json by default (ASGI)."""
        result = self.client.simulate_get('/hello')
        self.assertIn('application/json', result.headers.get('content-type', ''))

    def test_post_returns_201(self) -> None:
        """POST /hello must return HTTP 201 (ASGI)."""
        result = self.client.simulate_post('/hello', body='ping')
        self.assertEqual(result.status_code, 201)

    def test_post_echoes_body(self) -> None:
        """POST /hello must echo the request body as plain text (ASGI)."""
        result = self.client.simulate_post('/hello', body='ping')
        self.assertEqual(result.text, 'ping')

    def test_404_on_unknown_route(self) -> None:
        """An unmapped path must return HTTP 404 (ASGI)."""
        result = self.client.simulate_get('/no-such-route')
        self.assertEqual(result.status_code, 404)

    def test_405_on_disallowed_method(self) -> None:
        """A mapped path must return HTTP 405 for an unsupported method (ASGI)."""
        result = self.client.simulate_delete('/hello')
        self.assertEqual(result.status_code, 405)


if __name__ == '__main__':
    unittest.main()
