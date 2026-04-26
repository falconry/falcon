.. _faq_asgi_send_json:

How do I send JSON and URL-encoded requests to my Falcon app?
===============================================================

When testing or interacting with a Falcon ASGI/WSGI app, you need to send
data in the correct format with proper headers.

Sending JSON Data
-----------------

Use the ``application/json`` content type and serialize your payload:

.. code-block:: python

    import json
    import requests

    # Client side - sending JSON
    payload = {'image_data': 'message', 'key2': 'value2'}
    response = requests.post(
        "http://localhost:8000/translate",
        data=json.dumps(payload),
        headers={'Content-Type': 'application/json'}
    )

Receiving JSON in Falcon
~~~~~~~~~~~~~~~~~~~~~~~~

In your Falcon responder, use the built-in media handler (recommended):

.. code-block:: python

    import falcon

    class TextOcrRes:
        def on_post(self, req, resp):
            """Handles POST requests with JSON payload."""
            # Method 1: Using Falcon's built-in media handler (recommended)
            json_data = req.media  # Automatically parses JSON

            # Method 2: Manual parsing (if you need custom handling)
            # json_data = json.loads(req.bounded_stream.read().decode("utf-8"))

            print(json_data)
            resp.media = {'status': 'success', 'received': json_data}

    app = falcon.App()
    app.add_route('/translate', TextOcrRes())

Sending URL-encoded Data
------------------------

For ``application/x-www-form-urlencoded`` data, use ``data=`` parameter:

.. code-block:: python

    import requests

    # Client side - URL-encoded form data (default for requests)
    payload = {'field1': 'value1', 'field2': 'value2'}
    response = requests.post(
        "http://localhost:8000/endpoint",
        data=payload  # Automatically sets Content-Type to application/x-www-form-urlencoded
    )

Receiving URL-encoded Data in Falcon
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class FormHandler:
        def on_post(self, req, resp):
            """Handles POST requests with URL-encoded payload."""
            # Access form parameters
            field1 = req.get_param('field1')
            field2 = req.get_param('field2')

            # Or get all params as a dict
            params = req.params

            resp.media = {'field1': field1, 'field2': field2}

Using Falcon's Testing Module
------------------------------

For unit tests, use :class:`~falcon.testing.TestClient`:

.. code-block:: python

    from falcon.testing import TestClient

    def test_json_post(app):
        client = TestClient(app)

        # Simulate JSON request
        result = client.simulate_post(
            '/translate',
            json={'key': 'value'}  # Automatically sets Content-Type
        )
        assert result.status == falcon.HTTP_200

    def test_form_post(app):
        client = TestClient(app)

        # Simulate URL-encoded request
        result = client.simulate_post(
            '/endpoint',
            body='field1=value1&field2=value2',
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        assert result.status == falcon.HTTP_200

Common Pitfalls
---------------

1. **JSONDecodeError**: If you send ``data={'key': 'value'}`` (URL-encoded)
   but try ``json.loads()`` on it without the ``Content-Type: application/json``
   header. Always match your sending format with your parsing method.

2. **Missing Content-Type Header**: When using ``requests.post(url, data=json.dumps(payload))``,
   always add ``headers={'Content-Type': 'application/json'}``.

3. **Stream Already Consumed**: Use ``req.bounded_stream`` instead of
   ``req.stream`` if you need to read the raw body multiple times.
