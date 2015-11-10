from falcon import Request


class DebuggedApplication(object):

    """Enables pdb post-mortems for a given application"""

    def __init__(self, app):
        self.app = app

    def debug_application(self, environ, start_response):
        """Run the application and do post mortem on exception."""
        try:
            app_iter = self.app(environ, start_response)
            for item in app_iter:
                yield item
            if hasattr(app_iter, 'close'):
                app_iter.close()
        except Exception:
            import pdb
            pdb.post_mortem()

    def add_error_handler(self, exception, handler=None):
        pass

    def __call__(self, environ, start_response):
        """Dispatch the requests."""
        request = Request(environ)
        response = self.debug_application
        return response(environ, start_response)
