import io

import falcon.testing as testing
import six

unicode_message = u'Unicode: \x80'


class LoggerResource:

    def on_get(self, req, resp):
        req.log_error(unicode_message)

    def on_head(self, req, resp):
        req.log_error(unicode_message.encode('utf-8'))


class TestWSGIError(testing.TestBase):

    def before(self):
        self.tehlogger = LoggerResource()

        self.api.add_route('/logger', self.tehlogger)

        self.wsgierrors_buffer = io.BytesIO()

        if six.PY3:
            # Simulate Gunicorn's behavior under Python 3
            self.wsgierrors = io.TextIOWrapper(self.wsgierrors_buffer,
                                               line_buffering=True,
                                               encoding='utf-8')
        else:
            # WSGI servers typically present an open file object,
            # with undefined encoding, so do the encoding manually.
            self.wsgierrors = self.wsgierrors_buffer

    def test_responder_logged_bytestring(self):
        self.simulate_request('/logger', wsgierrors=self.wsgierrors)

        log = self.wsgierrors_buffer.getvalue()

        self.assertIn(unicode_message.encode('utf-8'), log)

    def test_responder_logged_unicode(self):
        if six.PY3:
            self.skipTest('Test only applies to Python 2')

        self.simulate_request('/logger', wsgierrors=self.wsgierrors,
                              method='HEAD')

        log = self.wsgierrors_buffer.getvalue()
        self.assertIn(unicode_message, log.decode('utf-8'))
