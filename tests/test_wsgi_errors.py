import io

import falcon.testing as testing
import six

unicode_message = u'Unicode: \x80'

if six.PY3:
    str_message = 'Unicode all the way: \x80'
else:
    str_message = 'UTF-8: \xc2\x80'


class LoggerResource:

    def on_get(self, req, resp):
        req.log_error(unicode_message)

    def on_head(self, req, resp):
        req.log_error(str_message)


class TestWSGIError(testing.TestSuite):

    def before(self):
        self.tehlogger = LoggerResource()

        self.api.add_route('/logger', self.tehlogger)

        self.wsgierrors_buffer = io.BytesIO()

        if six.PY3:
            # Simulate Gunicorn's behavior under Python 3
            self.wsgierrors = io.TextIOWrapper(self.wsgierrors_buffer,
                                               line_buffering=True)
        else:
            # WSGI servers typically present an open file object,
            # with undefined encoding, so do the encoding manually.
            self.wsgierrors = self.wsgierrors_buffer

    def test_responder_logged_unicode(self):
        self.simulate_request('/logger', wsgierrors=self.wsgierrors)

        log = self.wsgierrors_buffer.getvalue()
        self.assertIn(unicode_message.encode('utf-8'), log)

    def test_responder_logged_str(self):
        self.simulate_request('/logger', wsgierrors=self.wsgierrors,
                               method='HEAD')

        log = self.wsgierrors_buffer.getvalue()

        if six.PY3:
            self.assertIn(str_message.encode('utf-8'), log)
        else:
            self.assertIn(str_message, log)
