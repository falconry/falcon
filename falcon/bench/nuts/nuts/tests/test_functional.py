from unittest import TestCase
from webtest import TestApp
from nuts.tests import FunctionalTest


class TestRootController(FunctionalTest):

    def test_get(self):
        response = self.app.get('/')
        assert response.status_int == 200

    def test_search(self):
        response = self.app.post('/', params={'q': 'RestController'})
        assert response.status_int == 302
        assert response.headers['Location'] == ('https://pecan.readthedocs.io'
                                                '/en/latest/search.html'
                                                '?q=RestController')

    def test_get_not_found(self):
        response = self.app.get('/a/bogus/url', expect_errors=True)
        assert response.status_int == 404
