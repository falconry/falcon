.. _capitalizing_response_headers:

Capitalizing Response Header Names
==================================

Falcon always renders WSGI response header names in lower case; see
also: :ref:`faq_header_names_lowercase`

While this should normally never be an issue for standards-conformant HTTP
clients, it is possible to override HTTP headers using
`generic WSGI middleware
<https://www.python.org/dev/peps/pep-3333/#middleware-components-that-play-both-sides>`_:

.. code:: python

    class CustomHeadersMiddleware:

        def __init__(self, app, title_case=True, custom_capitalization=None):
            self._app = app
            self._title_case = title_case
            self._capitalization = custom_capitalization or {}

        def __call__(self, environ, start_response):
            def start_response_wrapper(status, response_headers, exc_info=None):
                if self._title_case:
                    headers = [
                        (self._capitalization.get(name, name.title()), value)
                        for name, value in response_headers]
                else:
                    headers = [
                        (self._capitalization.get(name, name), value)
                        for name, value in response_headers]
                start_response(status, headers, exc_info)

            return self._app(environ, start_response_wrapper)

We can now use this middleware to wrap a Falcon app:

.. code:: python

    import falcon

    # Import or define CustomHeadersMiddleware from the above snippet...


    class FunkyResource:

        def on_get(self, req, resp):
            resp.set_header('X-Funky-Header', 'test')
            resp.media = {'message': 'Hello'}


    app = falcon.App()
    app.add_route('/test', FunkyResource())

    app = CustomHeadersMiddleware(
        app,
        custom_capitalization={'x-funky-header': 'X-FuNkY-HeADeR'},
    )

As a bonus, this recipe applies to non-Falcon WSGI applications too.
