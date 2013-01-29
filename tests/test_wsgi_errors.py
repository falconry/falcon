import io
from . import helpers


class BombResource:

    def on_get(self, req, resp):
        raise IOError()

    def on_head(self, req, resp):
        raise MemoryError("I can't remember a thing.")


class LoggerResource:

    def on_get(self, req, resp):
        req.log_error('Internet crashed')


class TestWSGIError(helpers.TestSuite):

    def prepare(self):
        self.tehbomb = BombResource()
        self.tehlogger = LoggerResource()

        self.api.add_route('/bomb', self.tehbomb)
        self.api.add_route('/logger', self.tehlogger)
        self.wsgierrors = io.StringIO()

    def test_exception_logged(self):
        self._simulate_request('/bomb', wsgierrors=self.wsgierrors)
        log = self.wsgierrors.getvalue()

        self.assertIn('IOError', log)

    def test_exception_logged_with_details(self):
        self._simulate_request('/bomb', wsgierrors=self.wsgierrors,
                               method='HEAD')
        log = self.wsgierrors.getvalue()

        self.assertIn('MemoryError', log)
        self.assertIn('remember a thing', log)

    def test_responder_logged(self):
        self._simulate_request('/logger', wsgierrors=self.wsgierrors)
        log = self.wsgierrors.getvalue()

        self.assertIn('Internet crashed\n', log)
