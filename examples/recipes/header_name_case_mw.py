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
                    for name, value in response_headers
                ]
            else:
                headers = [
                    (self._capitalization.get(name, name), value)
                    for name, value in response_headers
                ]
            start_response(status, headers, exc_info)

        return self._app(environ, start_response_wrapper)
