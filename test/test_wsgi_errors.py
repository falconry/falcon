import io
from . import helpers


class BombResource:

    def on_get(self, req, resp):
        raise IOError()

    def on_head(self, req, resp):
        raise MemoryError()


class LoggerResource:

    def on_get(self, req, resp):
        pass


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

        self.assertIn(u'Responder raised IOError', log)
