import io

import pytest

import falcon
from falcon import testing
from falcon.util import compat

unicode_message = u'Unicode: \x80'


@pytest.fixture
def client():
    app = falcon.API()

    tehlogger = LoggerResource()
    app.add_route('/logger', tehlogger)
    return testing.TestClient(app)


class LoggerResource:

    def on_get(self, req, resp):
        req.log_error(unicode_message)

    def on_head(self, req, resp):
        req.log_error(unicode_message.encode('utf-8'))


class TestWSGIError(object):

    def setup_method(self, method):
        self.wsgierrors_buffer = io.BytesIO()

        if compat.PY3:
            # Simulate Gunicorn's behavior under Python 3
            self.wsgierrors = io.TextIOWrapper(self.wsgierrors_buffer,
                                               line_buffering=True,
                                               encoding='utf-8')
        else:
            # WSGI servers typically present an open file object,
            # with undefined encoding, so do the encoding manually.
            self.wsgierrors = self.wsgierrors_buffer

    def test_responder_logged_bytestring(self, client):
        client.simulate_request(path='/logger',
                                wsgierrors=self.wsgierrors,
                                query_string='amount=10')

        log = self.wsgierrors_buffer.getvalue()

        assert unicode_message.encode('utf-8') in log
        assert b'?amount=10' in log

    @pytest.mark.skipif(compat.PY3, reason='Test only applies to Python 2')
    def test_responder_logged_unicode(self, client):
        client.simulate_request(path='/logger',
                                wsgierrors=self.wsgierrors,
                                method='HEAD')
        log = self.wsgierrors_buffer.getvalue()
        assert unicode_message in log.decode('utf-8')
