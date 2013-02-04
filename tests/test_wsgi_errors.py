import io
import sys
from . import helpers


unicode_message = u'Unicode: \x80'

if sys.version_info[0] == 2:
    str_message = 'UTF-8: \xc2\x80'
else:
    str_message = 'Unicode all the way: \x80'


class BombResource:

    def on_get(self, req, resp):
        raise IOError()

    def on_head(self, req, resp):
        raise MemoryError("I can't remember a thing.")


class LoggerResource:

    def on_get(self, req, resp):
        req.log_error(unicode_message)

    def on_head(self, req, resp):
        req.log_error(str_message)


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

    def test_responder_logged_unicode(self):
        self._simulate_request('/logger', wsgierrors=self.wsgierrors)

        log = self.wsgierrors.getvalue()
        self.assertIn(unicode_message, log)

    def test_responder_logged_str(self):
        self._simulate_request('/logger', wsgierrors=self.wsgierrors,
                               method='HEAD')

        log = self.wsgierrors.getvalue()
        self.assertIn(str_message, log)
